# Apple Docs Harvest — FoundationModels + Evaluations + Speech (WWDC26 / iOS 27 era)

**Harvest date:** 2026-07-27 (all page timestamps `2026-07-27T19:07–19:11Z`)
**Method:** `https://developer.apple.com/documentation/X` → `https://sosumi.ai/documentation/X`, fetched with raw `curl -sL` (NOT WebFetch — WebFetch's summarizer model silently drops declarations). sosumi.ai returns YAML-frontmattered Markdown with `title:`, `description:`, `source:` (the real Apple URL), `timestamp:`, and `deprecated: true` when applicable.

> **Reproduce the harvest:**
> ```sh
> curl -sL --max-time 40 "https://sosumi.ai/documentation/foundationmodels/generationoptions" -o go.md
> ```
> Parentheses in Apple symbol paths MUST be preserved and quoted:
> `"/documentation/foundationmodels/systemlanguagemodel/tokencount(for:)"` — stripping them yields a 404 (606-byte error body).

**Everything below is grounded in a page I actually fetched this session.** Anything I inferred rather than read is explicitly marked `UNVERIFIED`.

---

## 0. TL;DR — what is new in the 2026 (iOS 27) release

From `/documentation/updates/foundationmodels` — **"June 2026"** section, verbatim:

> ### General
> - Build multimodal agentic app experiences by using the `LanguageModelSession.DynamicProfile` API.
> - Use the improved error types, like `LanguageModelError` for model-specific errors, `SystemLanguageModel.Error` for on-device Apple Foundation model errors, and `LanguageModelSession.Error` for errors related to the session but not the model.
>
> ### Models
> - Use the latest on-device `SystemLanguageModel` that follows instructions more accurately and produces better results, including in complex scenarios. Because the model changes when a person updates to iOS 27, iPadOS 27, macOS 27, and visionOS 27, test your prompts with the new model to verify your app's behavior.
> - Adopt the `LanguageModel` protocol to use any large language model — server or on-device — with the Foundation Models framework.
> - Use `PrivateCloudComputeLanguageModel` to access more reasoning capabilities and a larger context size.
> - Perform image analysis tasks by including an image in your prompt and using tools the Vision framework provides, like `OCRTool` and `BarcodeReaderTool`.
>
> ### Tool calling
> - Control how the model interacts with tools for your request by using `GenerationOptions.ToolCallingMode`.
>
> ### Instruments
> - Use the updated [Analyzing the runtime performance of your Foundation Models app] to get detailed insight into the complex workflows you build. The instrument provides insight into latency, prompts sent to the model, model output, tools and token usage, and so on.
>
> ### Open source
> - Get the **Foundation Models framework utilities** (`https://github.com/apple/foundation-models-utilities`) to access a collection of building blocks to help you explore emerging practices in working with large language models.
> - Use **CoreAILanguageModel** (`https://github.com/apple/coreai-models`) and **MLXLanguageModel** (`https://github.com/ml-explore/mlx-swift-lm`) to integrate on-device models with the Foundation Models framework.

**"March 2026":**
> - Use the **Foundation Models SDK for Python** (`https://github.com/apple/python-apple-fm-sdk`) to access the on-device foundation model at the core of Apple Intelligence.

**"February 2026"** (i.e. the 26.4 wave):
> - Use the latest on-device large language model that improves instruction-following and tool-calling abilities. Because the model changes when a person updates to iOS 26.4, iPadOS 26.4, macOS 26.4, and visionOS 26.4, test your prompts with the new model...
> - Reduce the possibility of blocking benign content with improved guardrails for `SystemLanguageModel`.
> - Measure how many tokens your prompt, instructions, or entire session transcript uses with `tokenCount(for:)`.
> - Use the `contextSize` property to get the maximum context size — in tokens — that the `SystemLanguageModel` supports.
> - Use the `#Playground` macro in Xcode to view an estimate of the usage of 4,096 tokens in the available context window. When you run the canvas, the output displays **Input Token Count** and **Response Token Count** separately.

From `/documentation/updates/speech` — **"June 2026"**, verbatim (that is the ENTIRE Speech changelog for 2026):
> - Access audio from a file, asset, or capture device, such as a microphone, by using `AssetInputSequenceProvider` or `CaptureInputSequenceProvider`.
> - Use `AnalyzerInputConverter` to convert `AVAudioBuffer` data into formats that `AnalyzerInput` supports.

---

## 1. Availability decoder ring (iOS 26 vs iOS 26.4 vs iOS 27)

sosumi.ai renders the availability line as `**Available on:** ...`. Observed distinct strings:

| Availability string | Meaning | Example symbols |
|---|---|---|
| `iOS 26.0+, iPadOS 26.0+, Mac Catalyst 26.0+, macOS 26.0+, visionOS 26.0+` | Original FM release, **no watchOS** | `SystemLanguageModel`, `SystemLanguageModel.UseCase`, `SystemLanguageModel.Guardrails`, `SystemLanguageModel.Availability`, `LanguageModelSession.init(model:tools:instructions:)`, `LanguageModelSession.init(model:tools:transcript:)`, `LanguageModelSession.GenerationError`, `LanguageModelSession.ToolCallError` |
| `iOS 26.0+, … visionOS 26.0+, watchOS 27.0+ Beta` | iOS 26 symbol that **gained watchOS in 27** | `LanguageModelSession`, `Transcript`, `Tool`, `Generable`, `GenerationSchema`, `DynamicGenerationSchema`, `GeneratedContent`, `GenerationGuide`, `GenerationID`, `Instructions`, `Prompt`, `GenerationOptions`, `GenerationOptions.SamplingMode`, `LanguageModelFeedback`, `Response`, `ResponseStream` |
| `iOS 26.4+, iPadOS 26.4+, Mac Catalyst 26.4+, macOS 26.4+, visionOS 26.4+` | **26.4 mid-cycle addition** | `SystemLanguageModel.tokenCount(for:)` |
| `iOS 27.0+ Beta, … watchOS 27.0+ Beta` | **Brand new in 2026** | everything in §3 |
| `iOS 26.0+, … tvOS 26.0+, visionOS 26.0+` | Speech framework baseline (**has tvOS**) | `SpeechAnalyzer`, `SpeechTranscriber`, `AnalyzerInput`, `AssetInventory`, `SpeechDetector` |
| `iOS 27.0+ Beta, … tvOS 27.0+ Beta, visionOS 27.0+ Beta` | New Speech 2026 | `AnalyzerInputConverter`, `AssetInputSequenceProvider`, `CaptureInputSequenceProvider` |
| `iOS 17.0+, … macOS 14.0+, visionOS 1.1+` | Legacy SFSpeech-era | `SFCustomLanguageModelData`, `SFSpeechLanguageModel`, `DataInsertable`, `TemplateInsertable` |

**Notable:** `contextSize` carries an explicit back-deployment attribute:
```swift
@backDeployed(before: iOS 26.4, macOS 26.4, visionOS 26.4)
final var contextSize: Int { get }
```
(from `/documentation/foundationmodels/systemlanguagemodel/contextsize`)

`DictationTranscriber` has **no tvOS** (`iOS 26.0+, iPadOS 26.0+, Mac Catalyst 26.0+, macOS 26.0+, visionOS 26.0+`) while `SpeechTranscriber` **does**. `structuredTranscript` availability omits Mac Catalyst: `iOS 27.0+ Beta, iPadOS 27.0+ Beta, macOS 27.0+ Beta, visionOS 27.0+ Beta, watchOS 27.0+ Beta`.

---

## 2. FoundationModels framework index — complete topic map

Source: `/documentation/foundationmodels`
Framework blurb: *"Perform tasks with models that specialize in language understanding, structured output, and tool calling."*
Framework availability: `iOS 26.0+, iPadOS 26.0+, Mac Catalyst 26.0+, macOS 26.0+, visionOS 26.0+, watchOS 27.0+ Beta`

Topic groups and their members (names verbatim from the index page):

- **Essentials** — Foundation Models updates; Generating content and performing tasks with Foundation Models; Adding intelligent app features with generative models
- **Sessions and Prompts** — Prompting an on-device foundation model; Managing the context window; Updating prompts for new model versions; `LanguageModelSession`; `Instructions`; `Prompt`; `Transcript`; `TranscriptErrorHandlingPolicy`; `GenerationOptions`; `ContextOptions`
- **Prompt Attachments** — Analyzing images with multimodal prompting; `Attachment`; `ImageAttachmentContent`; `ImageReference`
- **Dynamic Profiles** — Composing dynamic sessions with instructions and profiles; *Origami: Crafting a dynamic tutorial for Apple Intelligence*; `DynamicInstructions`; `DynamicInstructionsForEach`; `LanguageModelSession.DynamicProfile`; `LanguageModelSession.DynamicProfileModifier`; `LanguageModelSession.Profile`
- **Structured Output** — Generating Swift data structures with guided generation; `Generable`; `GenerationSchema`; `DynamicGenerationSchema`; `GeneratedContent`; `ConvertibleToGeneratedContent`; `ConvertibleFromGeneratedContent`
- **Tools** — Expanding generation with tool calling; *Generate dynamic game content with guided generation and tools*; `Tool`
- **System Language Model** — Supporting languages and locales with Foundation Models; Categorizing and organizing data with content tags; `SystemLanguageModel`; `LanguageModelError`
- **Private Cloud Compute** — Adding server-side intelligence with Private Cloud Compute; `com.apple.developer.private-cloud-compute` (entitlement); `PrivateCloudComputeLanguageModel`
- **Custom Language Model Provider** — Optimizing key-value caching in language model sessions; `LanguageModel`; `LanguageModelCapabilities`; `LanguageModelExecutor`; `LanguageModelExecutorGenerationChannel`; `LanguageModelExecutorGenerationRequest`
- **Custom Session Properties** — `LanguageModelSession.SessionProperty`; `SessionPropertyKey`; `SessionPropertyValues`; `SessionPropertyEntry()` (macro)
- **Safety** — Improving the safety of generative model output
- **Performance and Evaluation** — Evaluating prompts to measure performance and improve model responses; Evaluating language model responses (→ Evaluations framework); Analyzing the runtime performance of your Foundation Models app

Additional top-level symbols reachable from the index but not in a named group above:
`AnyDynamicInstructions`, `ConditionalDynamicInstructions`, `EmptyDynamicInstructions`, `TupleDynamicInstructions`, `DynamicInstructionsBuilder`, `InstructionsBuilder`, `InstructionsRepresentable`, `PromptBuilder`, `PromptRepresentable`, `GenerationGuide`, `GenerationID`, `LanguageModelFeedback`, macros `Generable(description:)`, `Generable(description:representNilExplicitlyInGeneratedContent:)`, `Generable(name:description:representNilExplicitlyInGeneratedContent:)`, `Guide(description:)`, `Guide(description:_:)`.

---

## 3. NEW-IN-2026 symbol inventory (all `iOS 27.0+ Beta` unless noted)

| Symbol | Kind | Declaration |
|---|---|---|
| `LanguageModelError` | Enumeration | `enum LanguageModelError` |
| `LanguageModelSession.Error` | Enumeration | `enum Error` |
| `SystemLanguageModel.Error` | Enumeration | `enum Error` *(no watchOS)* |
| `LanguageModel` | Protocol | `protocol LanguageModel : Sendable` |
| `LanguageModelCapabilities` | Structure | `struct LanguageModelCapabilities` |
| `LanguageModelCapabilities.Capability` | Structure | `struct Capability` |
| `LanguageModelExecutor` | Protocol | `protocol LanguageModelExecutor : Sendable` |
| `LanguageModelExecutorGenerationChannel` | Structure | `struct LanguageModelExecutorGenerationChannel` |
| `LanguageModelExecutorGenerationRequest` | Structure | `struct LanguageModelExecutorGenerationRequest` |
| `PrivateCloudComputeLanguageModel` | Class | `final class PrivateCloudComputeLanguageModel` |
| `DynamicInstructions` | Protocol | `protocol DynamicInstructions` |
| `DynamicInstructionsBuilder` | Structure | `@resultBuilder struct DynamicInstructionsBuilder` |
| `DynamicInstructionsForEach` | Structure | `struct DynamicInstructionsForEach<Data, ID, Content> where Data : RandomAccessCollection, ID : Hashable, Content : DynamicInstructions` |
| `LanguageModelSession.DynamicProfile` | Protocol | `protocol DynamicProfile` |
| `LanguageModelSession.DynamicProfileBuilder` | Structure | `@resultBuilder struct DynamicProfileBuilder` |
| `LanguageModelSession.DynamicProfileModifier` | Protocol | `protocol DynamicProfileModifier` |
| `LanguageModelSession.Profile` | Structure | `struct Profile` |
| `LanguageModelSession.SessionProperty` | Structure | `@propertyWrapper struct SessionProperty<Value>` |
| `SessionPropertyKey` | Protocol | `protocol SessionPropertyKey : SendableMetatype` |
| `SessionPropertyValues` | Class | `final class SessionPropertyValues` |
| `LanguageModelSession.Usage` | Structure | `struct Usage` |
| `ContextOptions` | Structure | `struct ContextOptions` |
| `ContextOptions.ReasoningLevel` | Enumeration | `enum ReasoningLevel` |
| `TranscriptErrorHandlingPolicy` | Structure | `struct TranscriptErrorHandlingPolicy` |
| `GenerationOptions.ToolCallingMode` | Structure | `struct ToolCallingMode` |
| `Attachment` | Structure | `struct Attachment<Content>` |
| `ImageAttachmentContent` | Structure | `struct ImageAttachmentContent` |
| `ImageReference` | Structure | `struct ImageReference` |
| `Transcript.Reasoning` | Structure | `struct Reasoning` |
| `Transcript.AttachmentSegment` | Structure | `struct AttachmentSegment` |
| `Transcript.ImageAttachment` | Structure | `struct ImageAttachment` |
| `Transcript.history` | Instance Property | `var history: ArraySlice<Transcript.Entry> { get set }` |
| `Transcript.structuredTranscript` | Instance Property | `var structuredTranscript: StructuredTranscript { get }` |

Also new but not individually fetched (listed on parent pages, `UNVERIFIED` declarations):
`LanguageModelSession.AnyDynamicProfile`, `LanguageModelSession.ConditionalDynamicProfile`, `LanguageModelSession.DynamicProfileModifierContent`, `LanguageModelSession.ModifiedDynamicProfile`, `AnyDynamicInstructions`, `ConditionalDynamicInstructions`, `EmptyDynamicInstructions`, `TupleDynamicInstructions`, `Transcript.CustomSegment`, `LanguageModelSession.Usage.Input`, `LanguageModelSession.Usage.Output`, `PrivateCloudComputeLanguageModel.QuotaUsage.LimitIncreaseSuggestion`, `PrivateCloudComputeLanguageModel.QuotaUsage.Status`, `PrivateCloudComputeLanguageModel.Availability`.

---

## 4. `LanguageModelSession`

Source: `/documentation/foundationmodels/languagemodelsession`

```swift
final class LanguageModelSession
```
Conforms to: `Copyable`, `Escapable`, `Observable` (Observation), `Sendable`, `SendableMetatype`.

Overview quote:
> A session is a single context that you use to generate content with, and maintains state between requests. You can reuse the existing instance or create a new one each time you call the model. When you create a session you can provide instructions that tells the model what its role is and provides guidance on how to respond.

```swift
let session = LanguageModelSession(instructions: """
    You are a motivational workout coach that provides quotes to inspire \
    and motivate athletes.
    """
)
let prompt = "Generate a motivational quote for my next workout."
let response = try await session.respond(to: prompt)
```

### 4.1 Initializers (verbatim declarations)

```swift
// iOS 26.0+ (no watchOS)
convenience init(model: SystemLanguageModel = .default,
                 tools: [any Tool] = [],
                 @InstructionsBuilder instructions: () throws -> Instructions) rethrows

// iOS 26.0+ (no watchOS) — "Start a session by rehydrating from a transcript."
convenience init(model: SystemLanguageModel = .default,
                 tools: [any Tool] = [],
                 transcript: Transcript)

// iOS 27.0+ Beta (no watchOS on this one) — "Create a session with dynamic instructions."
convenience init(model: some LanguageModel = SystemLanguageModel.default,
                 dynamicInstructions: sending some DynamicInstructions,
                 history: some Collection<Transcript.Entry> = [])

// iOS 27.0+ Beta — "Create a session with a profile."
convenience init(profile: sending some LanguageModelSession.DynamicProfile,
                 history: some Collection<Transcript.Entry> = [])
```

> **Gotcha:** the *legacy* inits are typed `model: SystemLanguageModel`, NOT `some LanguageModel`. Only the two dynamic-profile inits accept an arbitrary `LanguageModel`. But the PCC article says *"Because both `PrivateCloudComputeLanguageModel` and `SystemLanguageModel` conform to the `LanguageModel` protocol, you can pass either to `init(model:tools:instructions:)`."* — this is a **documentation contradiction** worth flagging; likely an unlisted iOS 27 overload of `init(model:tools:instructions:)` generic over `LanguageModel`. **UNVERIFIED which is correct.**

### 4.2 Response methods — full overload matrix

Six non-metadata + six metadata variants each for `respond` and `streamResponse` (24 methods total). Verbatim declarations fetched:

```swift
@discardableResult nonisolated(nonsending)
final func respond(to prompt: Prompt,
                   options: GenerationOptions = GenerationOptions())
  async throws -> LanguageModelSession.Response<String>

@discardableResult nonisolated(nonsending)
final func respond(options: GenerationOptions = GenerationOptions(),
                   @PromptBuilder prompt: () throws -> Prompt)
  async throws -> LanguageModelSession.Response<String>

@discardableResult nonisolated(nonsending)
final func respond<Content>(to prompt: Prompt,
                            generating type: Content.Type = Content.self,
                            includeSchemaInPrompt: Bool = true,
                            options: GenerationOptions = GenerationOptions())
  async throws -> LanguageModelSession.Response<Content> where Content : Generable

final func streamResponse<Content>(to prompt: Prompt,
                                   generating type: Content.Type = Content.self,
                                   includeSchemaInPrompt: Bool = true,
                                   options: GenerationOptions = GenerationOptions())
  -> sending LanguageModelSession.ResponseStream<Content> where Content : Generable

// iOS 27.0+ Beta — metadata family
@discardableResult nonisolated(nonsending)
final func respond(to prompt: Prompt,
                   options: GenerationOptions = GenerationOptions(),
                   contextOptions: ContextOptions = ContextOptions(),
                   metadata: [String : any Sendable & Codable & Equatable] = [:])
  async throws -> LanguageModelSession.Response<String>
```

Remaining names (declarations UNVERIFIED, listed on the class page):
`respond(schema:includeSchemaInPrompt:options:prompt:)`, `respond(to:schema:includeSchemaInPrompt:options:)`, `respond(generating:includeSchemaInPrompt:options:prompt:)`, and the metadata variants `respond(options:contextOptions:metadata:prompt:)`, `respond(generating:options:contextOptions:metadata:prompt:)`, `respond(schema:options:contextOptions:metadata:prompt:)`, `respond(to:generating:options:contextOptions:metadata:)`, `respond(to:schema:options:contextOptions:metadata:)` + the six `streamResponse` mirrors.

> **Note the metadata family drops `includeSchemaInPrompt`** — that moved into `ContextOptions.includeSchemaInPrompt`.

`includeSchemaInPrompt` discussion, verbatim:
> Consider using the default value of `true` for `includeSchemaInPrompt`. The exception to the rule is when the model has knowledge about the expected response format, either because it has been trained on it, or because it has seen exhaustive examples during this session.

**Streaming-in-background footgun**, verbatim from `streamResponse(to:generating:includeSchemaInPrompt:options:)`:
> **IMPORTANT** — If running in the background, use the non-streaming `respond(to:options:)` method to reduce the likelihood of encountering `LanguageModelError.rateLimited(_:)` errors.

### 4.3 Other members

```swift
final var isResponding: Bool { get }
final var transcript: Transcript { get set }          // note: settable
final func prewarm(promptPrefix: Prompt? = nil)
@discardableResult final func logFeedbackAttachment(
    sentiment: LanguageModelFeedback.Sentiment?,
    issues: [LanguageModelFeedback.Issue] = [],
    desiredOutput: Transcript.Entry? = nil) -> Data
```
Plus (iOS 27): `usage: LanguageModelSession.Usage`, `properties`, `transcriptErrorHandlingPolicy: TranscriptErrorHandlingPolicy`, `logFeedbackAttachment(sentiment:issues:desiredResponseContent:)`, `logFeedbackAttachment(sentiment:issues:desiredResponseText:)`.

`isResponding` discussion, verbatim:
> **IMPORTANT** — You should not call any of the respond methods while this property is `true`.
> Disable buttons and other interactions to prevent users from submitting a second prompt while the model is responding to their first prompt.

```swift
struct ShopView: View {
    @State var session = LanguageModelSession()
    @State var joke = ""

    var body: some View {
        Text(joke)
        Button("Generate joke") {
            Task {
                assert(!session.isResponding, "It should not be possible to tap this button while the model is responding")
                joke = try await session.respond(to: "Tell me a joke").content
            }
        }
        .disabled(session.isResponding) // Prevent concurrent calls to respond
    }
}
```

### 4.4 `Response` / `ResponseStream` / `Snapshot` / `Usage`

```swift
struct Response<Content> where Content : Generable        // iOS 26
struct ResponseStream<Content> where Content : Generable  // iOS 26, conforms to AsyncSequence
struct Snapshot                                            // ResponseStream.Snapshot
struct Usage                                               // iOS 27
```
- `Response`: `.content`, `.rawContent`, `.usage` (iOS 27), `.transcriptEntries`
- `ResponseStream`: `.collect()` → "The result from a streaming response, after it completes"; element type is `LanguageModelSession.ResponseStream.Snapshot`
- `Snapshot`: `.content`, `.rawContent`, `.transcriptEntries`, `.usage`
- `Usage`: `init(input:output:metadata:)`, `.input: Usage.Input`, `.output: Usage.Output`, `.metadata`, `.totalTokenCount`
  - `Usage.Input`: `init(totalTokenCount:cachedTokenCount:)`, `.totalTokenCount`, `.cachedTokenCount`
  - `Usage.Output`: `init(totalTokenCount:reasoningTokenCount:)`, `.totalTokenCount`, `.reasoningTokenCount`
  - `Usage.metadata` doc: *"Language models that provide other kinds of usage statistics may encode them in metadata."*

**Cache-hit-rate formula** (from the KV-caching article): *"determine your cache hit rate by dividing the cached input tokens by the total input tokens."*

---

## 5. Errors — the 2026 reshuffle

### 5.1 `LanguageModelError` (NEW, iOS 27)
```swift
enum LanguageModelError
```
Conforms: `Copyable`, `CustomDebugStringConvertible`, `Error`, `Escapable`, `LocalizedError`, `Sendable`, `SendableMetatype`.

Every case, with Apple's own one-liners:

| Case | Payload struct | Description |
|---|---|---|
| `.contextSizeExceeded(_:)` | `LanguageModelError.ContextSizeExceeded` | "The session's transcript exceeded the model's context size." |
| `.rateLimited(_:)` | `.RateLimited` | "The session has been rate limited." |
| `.refusal(_:)` | `.Refusal` | "The model refused to answer." |
| `.timeout(_:)` | `.Timeout` | "The request timed out before the model could produce a response." |
| `.guardrailViolation(_:)` | `.GuardrailViolation` | "The model's safety guardrails were triggered by content in a prompt or the response generated by the model." |
| `.unsupportedCapability(_:)` | `.UnsupportedCapability` | "The model being used doesn't support a particular feature." |
| `.unsupportedTranscriptContent(_:)` | `.UnsupportedTranscriptContent` | "The prompt contains content that the model cannot process." |
| `.unsupportedGenerationGuide(_:)` | `.UnsupportedGenerationGuide` | "An unsupported generation guide was used" |
| `.unsupportedLanguageOrLocale(_:)` | `.UnsupportedLanguageOrLocale` | "The model was prompted to respond in a language that it does not support." |

`LanguageModelError.ContextSizeExceeded` has `init(contextSize:tokenCount:debugDescription:metadata:)` and a `.tokenCount` property (from index link extraction).

### 5.2 `LanguageModelSession.Error` (NEW, iOS 27) — *session misuse*, not model failure
```swift
enum Error
```
- `.concurrentRequests` — "Multiple requests were made to the session concurrently."
- `.transcriptMutationWhileResponding` — "The session's transcript was mutated while a request was in progress."

Note these are **non-payload** cases, unlike the old `GenerationError.concurrentRequests(_:)`.

### 5.3 `SystemLanguageModel.Error` (NEW, iOS 27, no watchOS)
- `.assetsUnavailable(_:)` with payload `SystemLanguageModel.Error.AssetsUnavailable` (has `debugDescription`, `init(debugDescription:)`)

### 5.4 `PrivateCloudComputeLanguageModel.Error` (NEW, iOS 27)
- `.quotaLimitReached(_:)` → `.QuotaLimitReached` — "The allotted usage quota has been reached."
- `.networkFailure(_:)` → `.NetworkFailure` — "An error that occurs when a network is available, but PCC is inaccessible."
- `.serviceUnavailable(_:)` → `.ServiceUnavailable` — "Services are unavailable."

### 5.5 `LanguageModelSession.GenerationError` — **DEPRECATED**

Frontmatter carries `deprecated: true`. Availability `iOS 26.0+ … visionOS 26.0+` (no watchOS). Verbatim deprecation notice:

> **Deprecated**
> Use `LanguageModelError`, `SystemLanguageModel.Error`, or `LanguageModelSession.Error` instead. **Apps built with Xcode 26 will continue to catch this error until you rebuild with Xcode 27. You must update to Xcode 27 to catch the new error types before submitting your app.**

That last sentence is the single most important migration fact in the framework. Old cases (all marked *(Deprecated)*):
`.assetsUnavailable(_:)`, `.decodingFailure(_:)`, `.exceededContextWindowSize(_:)`, `.guardrailViolation(_:)`, `.rateLimited(_:)`, `.refusal(_:_:)` (**two** associated values), `.concurrentRequests(_:)`, `.unsupportedGuide(_:)`, `.unsupportedLanguageOrLocale(_:)`. Supporting types: `GenerationError.Context`, `GenerationError.Refusal`. Also `errorDescription`, `failureReason`, `recoverySuggestion`.

**Old → new mapping** (derived from names; some renames are non-obvious):
- `exceededContextWindowSize` → `LanguageModelError.contextSizeExceeded`
- `unsupportedGuide` → `LanguageModelError.unsupportedGenerationGuide`
- `assetsUnavailable` → `SystemLanguageModel.Error.assetsUnavailable`
- `concurrentRequests` → `LanguageModelSession.Error.concurrentRequests`
- `decodingFailure` → no obvious successor (**UNVERIFIED**; possibly `GeneratedContent.ParsingError`)

### 5.6 `LanguageModelSession.ToolCallError` (iOS 26, no watchOS)
```swift
struct ToolCallError            // Error, LocalizedError, Sendable
init(tool:underlyingError:)
var tool: ...                   // "The tool that produced the error."
var underlyingError: ...
var errorDescription: ...
```

### 5.7 `TranscriptErrorHandlingPolicy` (NEW, iOS 27)
```swift
struct TranscriptErrorHandlingPolicy   // Sendable, SendableMetatype
static let preserveTranscript   // "Keep the current transcript as is."
static let revertTranscript     // "Revert the transcript back to the state it was in just before the most recent request."
```
From the tool-calling article:
> When errors are thrown from a tool, the framework rolls back the transcript to a previously known valid state. Use `transcriptErrorHandlingPolicy` to define whether the session preserves the transcript an error occurs or if it reverts back to before the last request. **When preserving the transcript, the last entry may be partially generated.**

---

## 6. `SystemLanguageModel`

```swift
final class SystemLanguageModel      // iOS 26.0+, NO watchOS
```
Conforms: `Copyable`, `Escapable`, **`LanguageModel`**, `Observable`, `Sendable`, `SendableMetatype`.

**Three model versions**, verbatim:
> Apple periodically updates `SystemLanguageModel` in routine OS updates... Currently there are 3 model versions that align with:
> - iOS, iPadOS, macOS, and visionOS 26.0 - 26.3
> - iOS, iPadOS, macOS, and visionOS 26.4
> - iOS, iPadOS, macOS, visionOS, **and watchOS** 27.0

Members:
```swift
static var `default`: SystemLanguageModel                 // "The base version of the model."
convenience init(useCase: SystemLanguageModel.UseCase = .general,
                 guardrails: SystemLanguageModel.Guardrails = Guardrails.default)
var isAvailable: Bool
var availability: SystemLanguageModel.Availability
@backDeployed(before: iOS 26.4, macOS 26.4, visionOS 26.4)
final var contextSize: Int { get }
final var supportedLanguages: Set<Locale.Language> { get }
final func supportsLocale(_ locale: Locale = Locale.current) -> Bool
nonisolated(nonsending) final func tokenCount(for instructions: Instructions) async throws -> Int  // iOS 26.4+
```

`supportsLocale(_:)` discussion, verbatim:
> Use this method over `supportedLanguages` to check whether the given locale qualifies a user for using this model, as this method will take into consideration **language fallbacks**.

### `SystemLanguageModel.Availability`
```swift
@frozen enum Availability      // Equatable, Sendable, SendableMetatype
case available                 // "The system is ready for making requests."
case unavailable(_:)           // UnavailableReason
```
`UnavailableReason` cases: `.appleIntelligenceNotEnabled`, `.deviceNotEligible`, `.modelNotReady`.

Canonical switch (from the class page):
```swift
struct GenerativeView: View {
    private var model = SystemLanguageModel.default

    var body: some View {
        switch model.availability {
        case .available:
            // Show your intelligence UI.
        case .unavailable(.deviceNotEligible):
            // Show an alternative UI.
        case .unavailable(.modelNotReady):
            // The model isn't ready because it's downloading or because of other system reasons.
        case .unavailable(let other):
            // The model is unavailable for an unknown reason.
        }
    }
}
```

### `SystemLanguageModel.UseCase`
```swift
struct UseCase                 // Equatable, Sendable
static var general             // "A use case for general prompting."
static var contentTagging      // "A use case for content tagging."
```

### `SystemLanguageModel.Guardrails`
```swift
struct Guardrails              // Sendable, SendableMetatype (NOT Equatable)
static let `default`
static let permissiveContentTransformations: SystemLanguageModel.Guardrails
```
`default` doc: *"Guardrails that default to ensuring that the system blocks unsafe content in prompts and responses."*
`permissiveContentTransformations` doc: *"Guardrails that allow for permissively transforming text input, including potentially unsafe content, to text responses."*

### Content tagging recipe (from `categorizing-and-organizing-data-with-content-tags`)
```swift
// Create an instance of the on-device language model's content tagging use case.
let model = SystemLanguageModel(useCase: .contentTagging)

// Initialize a session with the model and instructions.
let session = LanguageModelSession(model: model, instructions: """
    Provide the two tags that are most significant in the context of topics.
    """
)
```
```swift
@Generable
struct ContentTaggingResult {
    @Guide(description: "Most important actions in the input text.", .maximumCount(2))
    let actions: [String]
    @Guide(description: "Most important emotions in the input text.", .maximumCount(3))
    let emotions: [String]
    @Guide(description: "Most important objects in the input text.", .maximumCount(5))
    let objects: [String]
    @Guide(description: "Most important topics in the input text.", .maximumCount(2))
    let topics: [String]
}
```
```swift
let response = try await session.respond(to: prompt, generating: ContentTaggingResult.self)
```
The four categories the content-tagging use case is trained for are therefore: **actions, emotions, objects, topics**.
</content>
</invoke>

---

## 7. `GenerationOptions` + `ContextOptions`

Source: `/documentation/foundationmodels/generationoptions`

```swift
struct GenerationOptions       // Equatable, Sendable, SendableMetatype
```

Overview, verbatim:
> Generation options determine the decoding strategy the framework uses to adjust the way the model chooses output tokens. When you interact with the model, it converts your input to a token sequence, and uses it to generate the response.
>
> Only use `maximumResponseTokens` when you need to protect against unexpectedly verbose responses. **Enforcing a strict token response limit can lead to the model producing malformed results or grammatically incorrect responses.**
>
> All input to the model contributes tokens to the context window of the `LanguageModelSession` — including the `Instructions`, `Prompt`, `Tool`, and `Generable` types, and the model's responses. If your session exceeds the available context size, it throws `LanguageModelError.contextSizeExceeded(_:)`.

### Initializers
```swift
// iOS 26
init(samplingMode:temperature:maximumResponseTokens:)

// iOS 27.0+ Beta — verbatim
init(samplingMode: GenerationOptions.SamplingMode? = nil,
     temperature: Double? = nil,
     maximumResponseTokens: Int? = nil,
     toolCallingMode: GenerationOptions.ToolCallingMode?)

// DEPRECATED
init(sampling:temperature:maximumResponseTokens:)
```
> **Footgun:** in the iOS 27 four-arg init, `toolCallingMode` has **no default value** while the other three do. So `GenerationOptions(toolCallingMode: .required)` compiles (other args defaulted) but you cannot omit `toolCallingMode` and still select that overload.

### Properties
```swift
var temperature: Double?                       // iOS 26
var maximumResponseTokens: Int?                // iOS 26
var samplingMode: GenerationOptions.SamplingMode?   // iOS 26 (property name `samplingMode-swift.property`)
var toolCallingMode: GenerationOptions.ToolCallingMode?  // iOS 27
var sampling                                   // *(Deprecated)* — replaced by `samplingMode`
```

### `GenerationOptions.SamplingMode`
```swift
struct SamplingMode            // Equatable, Sendable, SendableMetatype
```
> A model builds its response to a prompt in a loop. At each iteration in the loop the model produces a probability distribution for all the tokens in its vocabulary. The sampling mode controls how a token is selected from that distribution.

```swift
static var greedy: GenerationOptions.SamplingMode
    // "A sampling mode that always chooses the most likely token."

static func random(top k: Int, seed: UInt64? = nil) -> GenerationOptions.SamplingMode
    // "A sampling mode that considers a fixed number of high-probability tokens." (top-k)

static func random(probabilityThreshold: Double, seed: UInt64? = nil) -> GenerationOptions.SamplingMode
    // "A mode that considers a variable number of high-probability tokens based on the specified threshold." (top-p / nucleus)
```
`random(top:seed:)` discussion, verbatim:
> Also known as top-k. During the token-selection process, the vocabulary is sorted by probability a token is selected from among the top K candidates. Smaller values of K will ensure only the most probable tokens are candidates for selection, resulting in more deterministic and confident answers. Larger values of K will allow less probably tokens to be selected, raising non-determinism and creativity.

`random(probabilityThreshold:seed:)` discussion, verbatim:
> Also known as top-p or nucleus sampling. With nucleus sampling, tokens are sorted by probability and added to a pool of candidates until the cumulative probability of the pool exceeds the specified threshold, and then a token is sampled from the pool.
> Because the number of tokens isn't predetermined, the selection pool size will be larger when the distribution is flat and smaller when it is spikey.

`probabilityThreshold` param doc: *"A number between `0.0` and `1.0` that increases sampling pool size."*

> **Seed footgun (stated on BOTH `random` pages):** "Setting a random seed is **not guaranteed** to result in fully deterministic output. It is **best effort**."

Nested: `GenerationOptions.SamplingMode.Kind` (enum) with cases `greedy`, `randomProbabilityThreshold(_:seed:)`, `randomTopK(_:seed:)`, plus a `kind` property. **Note the Kind case is `randomTopK` while the factory is `random(top:seed:)`.**

### `GenerationOptions.ToolCallingMode` (NEW iOS 27)
```swift
struct ToolCallingMode         // Equatable, Sendable, SendableMetatype
static var allowed             // "The model may or may not call tools."
static var disallowed          // "The model may not call any tool."
static var required            // "The model must call one or multiple tools."
var kind: GenerationOptions.ToolCallingMode.Kind
```
`Kind` enum cases: `allowed`, `disallowed`, `required`.

> **CRITICAL FOOTGUN** (stated verbatim on both the ToolCallingMode page and the tool-calling article):
> When you set the mode to `required`, you must define an exit condition by either throwing an error from a tool's `call(arguments:)` method or by changing the mode dynamically using a `LanguageModelSession.DynamicProfile`; **otherwise, the model continues to call the tool.**

The canonical escape pattern:
```swift
extension SessionPropertyValues {
    @SessionPropertyEntry
    var toolCallCount: Int = 0
}

struct RecipeDynamicProfile: LanguageModelSession.DynamicProfile {
    @SessionProperty(\.toolCallCount)
    var toolCallCount
    var body: some LanguageModelSession.DynamicProfile {
        Profile {
            BreadDatabaseTool()
        }
        .toolCallingMode(toolCallCount < 1 ? .required : .allowed)
        .onToolCall {
            toolCallCount += 1
        }
    }
}
```

Call-site usage:
```swift
let response = try await session.respond(
    to: "What's a good sourdough recipe?",
    options: GenerationOptions(toolCallingMode: .required)
)

let response = try await session.respond(
    to: "Summarize the recipes you found",
    options: GenerationOptions(toolCallingMode: .disallowed)
)
```

### `ContextOptions` (NEW iOS 27)
```swift
struct ContextOptions          // Equatable, Sendable, SendableMetatype
init(includeSchemaInPrompt:reasoningLevel:)
var includeSchemaInPrompt      // "Inject the schema into the prompt to bias the model."
var reasoningLevel: ContextOptions.ReasoningLevel
```
> Create a `ContextOptions` structure when you need to bias the model's behavior by adjusting how the model receives your prompt.

```swift
enum ReasoningLevel            // Equatable, Sendable, SendableMetatype
case light      // "A level that indicates light thinking that's good for quick responses."
case moderate   // "A level that indicates a moderate amount thinking."
case deep       // "A level that indicates deep thinking that's good for more analysis over a request."
case custom(_:) // "A custom level that indicates a level not supported by the other cases."
```

Usage (from the PCC article):
```swift
let response = try await session.respond(
    to: "What are the tradeoffs in this architecture?",
    contextOptions: ContextOptions(reasoningLevel: .deep)
)
```
> To determine what reasoning level to use, evaluate your feature by starting with `.moderate`. Use `.deep` when you determine the task needs additional reasoning, like when you're making architectural decisions with many competing constraints. Deep reasoning is slower, but it spends more time catching things that the other levels miss.
> The more reasoning you apply causes the model to use more of the context window... **Reasoning segments reflect the model's intermediate reasoning and don't appear in the final response content.**

---

## 8. Guided generation: `Generable`, `@Guide`, schemas

### `Generable`
```swift
protocol Generable : ConvertibleFromGeneratedContent, ConvertibleToGeneratedContent
```
Inherits: `ConvertibleFromGeneratedContent`, `ConvertibleToGeneratedContent`, `InstructionsRepresentable`, `PromptRepresentable`, `SendableMetatype`.
Conforming framework types: **`GeneratedContent`**, **`ImageReference`**.

Canonical example (verbatim):
```swift
@Generable
struct SearchSuggestions {
    @Guide(description: "A list of suggested search terms.", .count(4))
    var searchTerms: [SearchTerm]
    @Generable
    struct SearchTerm {
        // Use a generation identifier for data structures the framework generates.
        var id: GenerationID
        @Guide(description: "A two- or three- word search term, like 'Beautiful sunsets'.")
        var searchTerm: String
    }
}
```

Token-cost guidance, verbatim:
> For every `Generable` type in a request, the framework converts its type and format information to a JSON schema and provides it to the model. This contributes to the available context window size... To reduce the size of your generable type:
> - Reduce the complexity of your `Generable` type by evaluating whether properties are necessary to complete the task.
> - Give your properties short and clear names.
> - Use `Guide(description:)` on properties only when it improves response quality.
> - Add a `Guide(description:_:)` with `maximumCount(_:)` to reduce token usage.

Protocol members:
```swift
static var generationSchema: GenerationSchema { get }
func asPartiallyGenerated() -> Self.PartiallyGenerated
associatedtype PartiallyGenerated   // "A representation of partially generated content"
```

### Macros
```swift
@Generable(description:)
@Generable(description:representNilExplicitlyInGeneratedContent:)
@Generable(name:description:representNilExplicitlyInGeneratedContent:)   // "using a custom name for the schema instead of the Swift type name"
@Guide(description:)
@Guide(description:_:)          // second param is one or more GenerationGuide values
```
`@Guide` can be **stacked** (two attributes on one property) — from `managing-the-context-window`:
```swift
@Generable
struct GameSettings {
    @Guide(.minimumCount(1), .maximumCount(20))
    @Guide(description: "Keyboard shortcuts for desktop")
    var keyboardShortcuts: [String]
}
```
> Note there is also a `@Guide(_ guides:)`-style form used above with **no** description — `@Guide(.minimumCount(1), .maximumCount(20))`. Neither documented macro signature (`Guide(description:)` / `Guide(description:_:)`) matches this exactly, so a variadic-guides-only overload exists. **UNVERIFIED signature.**

### `GenerationGuide`
```swift
struct GenerationGuide<Value>          // iOS 26.0+ … watchOS 27.0+ Beta
```
Complete static member list with Apple's descriptions:

| Guide | Description |
|---|---|
| `pattern(_:)` | "Enforces that the string follows the pattern." |
| `element(_:)` | "Enforces a guide on the elements within the array." |
| `count(_:)` | "Enforces that the array has exactly a certain number elements." |
| `constant(_:)` | "Enforces that the string be precisely the given value." |
| `anyOf(_:)` | "Enforces that the string be one of the provided values." |
| `range(_:)` | "Enforces values fall within a range." |
| `minimum(_:)` | "Enforces a minimum value." |
| `minimumCount(_:)` | "Enforces a minimum number of elements in the array." |
| `maximum(_:)` | "Enforces a maximum value." |
| `maximumCount(_:)` | "Enforces a maximum number of elements in the array." |

Observed usages: `.count(4)`, `.count(3...8)` (range form!), `.range(0...20)`, `.range(1...10)`, `.minimum(1)`, `.maximum(10)`, `.maximumCount(2)`, `.minimumCount(1)`.
> `.count(3...8)` appears in the Evaluations model-judge article — so `count` accepts **both** an `Int` and a `ClosedRange<Int>`. **UNVERIFIED as separate overloads.**

If an unsupported guide reaches the model: `LanguageModelError.unsupportedGenerationGuide(_:)` (was `GenerationError.unsupportedGuide(_:)`).

### `GenerationID`
```swift
struct GenerationID            // iOS 26.0+ … watchOS 27.0+ Beta
```
> "A unique identifier that is stable for the duration of a response, but not across responses."

Verbatim SwiftUI streaming example (note: this snippet in Apple's docs is **syntactically broken** — unbalanced braces and a stray `try!` — reproduced as-is):
```swift
@Generable struct Person: Equatable {
    var id: GenerationID
    var name: String
}

struct PeopleView: View {
    @State private var session = LanguageModelSession()
    @State private var people = [Person.PartiallyGenerated]()

    var body: some View {
        // A person's name changes as the response is generated,
        // and two people can have the same name, so it is not suitable
        // for use as an id.
        //
        // `GenerationID` receives special treatment and is guaranteed
        // to be both present and stable.
        List {
            ForEach(people) { person in
                Text("Name: \(person.name)")
            }
        }
        .task {
            do {
                for try! await people in stream.streamResponse(
                    to: "Who were the first 3 presidents of the US?",
                    generating: [Person].self
                ) {
                    withAnimation {
                        self.people = people
                }
            } catch {
                // Handle the thrown error.
            }
        }
    }
}
```

### `GenerationSchema`
```swift
struct GenerationSchema        // Copyable, CustomDebugStringConvertible, Decodable, Encodable, Escapable, Sendable
```
Initializers:
```swift
init(root:dependencies:)                                              // from DynamicGenerationSchema
init(type:description:anyOf:)                                         // "Creates a schema for a string enumeration."
init(type:description:properties:)
init(type:description:representNilExplicitlyInGeneratedContent:properties:)
```
`var name: String`. Nested `GenerationSchema.Property` with `init(name:description:type:guides:)`.

`GenerationSchema.SchemaError` cases:
- `.duplicatePropertySchema:property:context:`
- `.duplicateTypeSchema:type:context:`
- `.emptyTypeChoicesSchema:context:`
- `.undefinedReferencesSchema:references:context:`
Plus `SchemaError.Context` (`debugDescription`, `init(debugDescription:)`), `errorDescription`, `recoverySuggestion`.

### `DynamicGenerationSchema`
```swift
struct DynamicGenerationSchema     // Sendable, SendableMetatype
```
> An individual schema may reference other schemas by name, and references are resolved when converting a set of dynamic schemas into a `GenerationSchema`.

```swift
init(arrayOf:minimumElements:maximumElements:)
init(name:description:anyOf:)
init(name:description:properties:)
init(name:description:representNilExplicitlyInGeneratedContent:properties:)
init(referenceTo:)                 // "Creates an refrence schema." [sic — Apple typo]
init(type:guides:)                 // "Creates a schema from a generable type and guides."
static var null                    // "Creates a null schema."
struct DynamicGenerationSchema.Property   // init(name:description:schema:isOptional:)
```

Runtime-schema walkthrough (from `generating-swift-data-structures-with-guided-generation`):
```swift
// Create the dynamic schema at runtime.
let menuSchema = DynamicGenerationSchema(
    name: "Menu",
    properties: [
        DynamicGenerationSchema.Property(
            name: "dailySoup",
            schema: DynamicGenerationSchema(
                name: "dailySoup",
                anyOf: ["Tomato", "Chicken Noodle", "Clam Chowder"]
            )
        )

        // Add additional properties.
    ]
)
```
```swift
// Create the schema.
let schema = try GenerationSchema(root: menuSchema, dependencies: [])

// Pass the schema to the model to guide the output.
let response = try await session.respond(
    to: "The prompt you want to make.",
    schema: schema
)
```

Also from that article — **primitives work directly**:
```swift
let prompt = "How many tablespoons are in a cup?"
let session = LanguageModelSession(model: .default)

// Generate a response with the type `Float`, instead of `String`.
let response = try await session.respond(to: prompt, generating: Float.self)
```
```swift
@Generable(description: "Basic profile information about a cat")
struct CatProfile {
    // A guide isn't necessary for basic fields.
    var name: String

    @Guide(description: "The age of the cat", .range(0...20))
    var age: Int

    @Guide(description: "A one sentence profile about the cat's personality")
    var profile: String
}
```

### `GeneratedContent`
```swift
struct GeneratedContent        // conforms to Generable itself
```
> Generated content may contain a single value, an array, or key-value pairs with unique keys.

Initializers: `init(_:)`, `init(_:id:)`, `init(elements:id:)`, `init(properties:id:)`, `init(properties:id:uniquingKeysWith:)`, **`init(json:)`** ("Creates equivalent content from a JSON string"), `init(kind:id:)`.

Accessors: `kind`, `value(_:)`, `value(_:forProperty:)`, **`isComplete`** ("A Boolean that indicates whether the generated content is completed"), `generatedContent`, **`jsonString`**, `debugDescription`, `id`.

`GeneratedContent.Kind` enum cases: `.array(_:)`, `.bool(_:)`, `.null`, `.number(_:)`, `.string(_:)`, `.structure(properties:orderedKeys:)`.

`GeneratedContent.ParsingError`: `init(rawContent:underlyingError:debugDescription:)`, `.rawContent`, `.underlyingError`, `.debugDescription`.

---

## 9. `Tool` protocol

```swift
protocol Tool<Arguments, Output> : Sendable      // iOS 26.0+ … watchOS 27.0+ Beta
@concurrent func call(arguments: Self.Arguments) async throws -> Self.Output
```

Requirements: `name`, `description`, `parameters` ("A schema for the parameters this tool accepts"), `includesSchemaInInstructions` ("If true, the model's name, description, and parameters schema will be injected into the instructions of sessions that leverage this tool"), `Arguments`, `Output`, plus `Tool.SessionProperty` (iOS 27).

Overview quote:
> A `Tool` defines a `call(arguments:)` method that takes arguments that conforms to `ConvertibleFromGeneratedContent`, and returns an output of any type that conforms to `PromptRepresentable`... Typically, `Output` is a `String` or any `Generable` types.
> Tools must conform to `Sendable` so the framework can run them concurrently. **If the model needs to pass the output of one tool as the input to another, it executes back-to-back tool calls.**
> You control the life cycle of your tool, so you can track the state of it between calls to the model.

Canonical tool:
```swift
struct FindContacts: Tool {
    let name = "findContacts"
    let description = "Finds a specific number of contacts"

    @Generable
    struct Arguments {
        @Guide(description: "The number of contacts to get", .range(1...10))
        let count: Int
    }

    func call(arguments: Arguments) async throws -> [String] {
        var contacts: [CNContact] = []
        // Fetch a number of contacts using the arguments.
        let formattedContacts = contacts.map {
            "\($0.givenName) \($0.familyName)"
        }
        return formattedContacts
    }
}
```

Six-phase tool loop, verbatim from `expanding-generation-with-tool-calling`:
> 1. You present a list of available tools and their parameters to the model.
> 2. You submit your prompt to the model.
> 3. The model generates arguments to the tool(s) it wants to invoke.
> 4. Your tool runs code on behalf of the model, using the model's generated arguments.
> 5. Your tool passes its output back to the model.
> 6. The model produces a final response to the prompt, based on the tool output.

Parallel tool calls are supported ("The model can call a tool multiple times in parallel to satisfy the request, like when retrieving weather details for several cities").

Tool error handling:
```swift
do {
    let answer = try await session.respond(to: "Find a recipe for tomato soup.")
} catch let error as LanguageModelSession.ToolCallError {

    // Access the name of the tool, like BreadDatabaseTool.
    print(error.tool.name)

    // Access an underlying error that your tool throws and check if the tool
    // encounters a specific condition.
    if case .databaseIsEmpty = error.underlyingError as? SearchBreadDatabaseToolError {
        // Display an error in the UI.
    }

} catch {
    print("Some other error: \(error)")
}
```

Tool-budget guidance (from `managing-the-context-window`):
> - Limit tool descriptions and `@Guide` annotations to short phrases.
> - **Provide no more than three to five tools per request.**
> - Skip tool calling when you don't need the model to make decisions. If the model always needs specific information, retrieve it directly and include it in your prompt rather than relying on tool calling.

An `@Observable final class` can conform to `Tool` (from the context-window article):
```swift
@Observable
final class FindPointsOfInterestTool: Tool {
    let name = "findPointsOfInterest"
    let description = "Finds points of interest for a landmark."

    @Generable
    enum Category: String, CaseIterable {
        case campground
        case hotel
        case cafe
        case museum
        case marina
        case restaurant
        case nationalMonument
    }

    @Generable
    struct Arguments {
        @Guide(description: "The type of destination to look up.")
        let pointOfInterest: Category

        @Guide(description: "The natural language query of what to search for.")
        let naturalLanguageQuery: String
    }

    func call(arguments: Arguments) async throws -> String {
        // Implement the logic your app needs when the model calls this tool.
    }
}
```

---

## 10. Dynamic Profiles (the flagship 2026 feature)

Primary source: `/documentation/foundationmodels/composing-dynamic-sessions-with-instructions-and-profiles`

Framing quote:
> By default, a language model session evaluates instructions upon initialization, and they remain static for the session. The dynamic profiles API allows you to build your app so a session uses only what's necessary based on the state of your app. When the context of your app changes, the instructions, tools, and model configuration change with it.
> **Because the body of dynamic instructions re-evaluates before each call to the model, the model always sees a snapshot of your app's current state.**

Three composable layers: `DynamicInstructions` (what the model sees) → `LanguageModelSession.Profile` (binds content to one configuration) → `LanguageModelSession.DynamicProfile` (orchestrates which Profile is active).

### 10.1 `DynamicInstructions`
```swift
protocol DynamicInstructions            // iOS 27.0+ Beta
var body: Self.Body { get }
associatedtype Body
// nested: DynamicInstructions.ForEach, DynamicInstructions.SessionProperty
```
Conforming types: `AnyDynamicInstructions`, `ConditionalDynamicInstructions`, `DynamicInstructionsForEach`, `EmptyDynamicInstructions`, **`Instructions`**, `TupleDynamicInstructions`.
Builder: `@resultBuilder struct DynamicInstructionsBuilder`.

> In the `body` of your type, include any `Instructions` block, `Tool` instances, and nested `DynamicInstructions`.

```swift
struct PresentationInstructions: DynamicInstructions {
    // The data source for conditional instructions.
    var isEditingImage = true
    var isEditingAnimation = false

    var body: some DynamicInstructions {
        // The instructions and tools that remain the same across any use of this type.
        Instructions {
            "Help people improve their presentation."
        }
        ListPhotosTool()
        AddPhotoTool()

        // Depending on the state of the app, include additional instructions
        // that provide the model with more task-specific instructions and tools.
        if isEditingImage {
            ImageEditingInstructions()
        }

        if isEditingAnimation {
            AnimationEditingInstructions()
        }
    }
}
```
```swift
let session = LanguageModelSession(
    dynamicInstructions: PresentationInstructions()
)
```
> **IMPORTANT** — When conditionally providing instructions and tools, **append them in place** to improve latency from the use of model caching.

### 10.2 `LanguageModelSession.Profile`
```swift
struct Profile                          // conforms to LanguageModelSession.DynamicProfile
init(_:)                                // "Creates a profile that contains dynamic instructions."
```
```swift
Profile {
    // Custom instructions and tools for a creative task.
}
// Use an instance of the PCC model you create in the parent profile.
.model(pccModel)
// Use a higher creative temperature value when a person likes poetry.
.temperature(likesPoetry ? 0.8 : 0.1)
// Perform deeper reasoning when a person likes astronomy.
.reasoningLevel(likesAstronomy ? .deep : .light)
```

### 10.3 `LanguageModelSession.DynamicProfile`
```swift
protocol DynamicProfile                 // iOS 27.0+ Beta
var body: Self.Body { get }
associatedtype Body
```
Conforming types: `AnyDynamicProfile`, `ConditionalDynamicProfile`, `DynamicProfileModifierContent`, `ModifiedDynamicProfile`, **`Profile`**.
Nested: `DynamicProfile.DynamicProfile`, `DynamicProfile.Profile`, `DynamicProfile.SessionProperty`.

> A dynamic profile is the top-level coordination layer that manages profiles. It determines which `Profile` is in an active state and allows a `LanguageModelSession` to switch between entirely different configurations as app state changes. **A body must resolve to a single profile.**

> A `LanguageModelSession.DynamicProfileBuilder` **enforces a hard constraint at compile time so exactly one `Profile` is active at a time.** Instead of using parallel `if` blocks, use expressions so the compiler verifies the constraint.

```swift
struct PresentationProfile: LanguageModelSession.DynamicProfile {
    // Create an instance to the server model.
    var pccModel = PrivateCloudComputeLanguageModel()

    // The data source for the profile.
    var isEditingImage = true
    var isEditingAnimation = false

    // Determine which profile to load based on the current state.
    var body: some LanguageModelSession.DynamicProfile {
        if isEditingImage {
            Profile {
                ImageEditingInstructions()
            }
        } else if isEditingAnimation {
            Profile {
                AnimationEditingInstructions()
            }
            .model(pccModel)
            .temperature(0.2)
            .reasoningLevel(.light)
        } else {
            Profile {
                PresentationDynamicInstructions()
            }
            .temperature(0.8)
        }
    }
}
```
```swift
let session = LanguageModelSession(
    profile: PresentationProfile()
)
```

### 10.4 Complete modifier list on `DynamicProfile`

**Value modifiers (configuring the model):**
| Modifier | Description |
|---|---|
| `model(_:)` | "Sets the model." |
| `temperature(_:)` | "Sets the model temperature." |
| `samplingMode(_:)` | "Sets the samping mode." *[Apple typo]* |
| `reasoningLevel(_:)` | "Sets the reasoning level." |
| `maximumResponseTokens(_:)` | "Sets the maximum response tokens." |
| `toolCallingMode(_:)` | (tool modifier group) |
| `transcriptErrorHandlingPolicy(_:)` | "The session's policy for managing the transcript when errors occur." |
| `modifier(_:)` | "Apply a modifier to the dynamic profile." |

**Life cycle modifiers:**
| Modifier | When it runs (verbatim from article) |
|---|---|
| `onActivate(perform:)` | "Runs when the profile becomes active and allows for set up work." |
| `onDeactivate(perform:)` | "Runs when the profile becomes inactive and allows for teardown work." |
| `onPrompt(perform:)` | "Runs after the user prompt appends to the transcript, but before the model request starts." |
| `onResponse(perform:)` | "Runs after the model produces a response." |
| `onToolCall(perform:)` | "Runs when the model invokes a tool." |
| `onToolOutput(perform:)` | "Runs when a tool call produces output." |
| `onReasoning(perform:)` | "Runs an action whenever this dynamic profile produces reasoning." *(listed under generic "Instance Methods", not in the article's table)* |

**History:**
| Modifier | Description |
|---|---|
| `historyTransform(_:)` | "Apply a transformation to the history prior to invoking the model." |

### 10.5 Three-tier modifier precedence (verbatim)

> When the same modifier appears at multiple levels, a three-tier precedence rule determines which value to use — from highest to lowest priority:
> 1. **Call-site arguments** — Generation options you pass directly to `respond(to:options:)` override all profile and dynamic profile modifiers.
> 2. **Innermost dynamic profile or profile modifier** — The modifier closest to the subprofile declaration overrides a dynamic profile.
> 3. **Dynamic profile modifiers** — Act as defaults that apply to all subprofiles unless the modifier is overridden by a subprofile.

> Unlike value modifiers, **life cycle callbacks accumulate across nested profiles**. When a profile and a subprofile both register a callback, the framework calls both.

```swift
// A top-level dynamic profile that includes a single subprofile.
struct WritingProfile: LanguageModelSession.DynamicProfile {
    var body: some LanguageModelSession.DynamicProfile {
        // By default, the temperature value applies to both branches in
        // `WritingContent` unless a branch adds a temperature modifier.
        WritingContent()
            .temperature(0.5)
    }
}

// A dynamic profile that contains two states.
struct WritingContent: LanguageModelSession.DynamicProfile {
    // A custom writing mode that determines which subprofile to use.
    var mode: MyCustomWritingMode = .creative

    var body: some LanguageModelSession.DynamicProfile {
        switch mode {
        case .creative:
            // Use the temperature `1.0` because the profile-level modifier takes priority.
            Profile {
                CreativeWritingInstructions()
            }
            .temperature(1.0)
        case .technical:
            // Inherit the temperature `0.5` from `WritingProfile`.
            Profile {
                TechnicalWritingInstructions()
            }
        }
    }
}
```

### 10.6 Life cycle callbacks as validation checkpoints

> Throwing an error inside a life cycle callback propagates to the caller's `respond(to:options:)` or `streamResponse(to:options:)` call, letting you raise errors that surface directly to your call site.

```swift
Profile {
    MyCustomFileAccessInstructions()
    MyCustomReadFileTool()
}
.onToolCall { toolCall in
    // Runs before the framework invokes the tool and allows for checking
    // whether the app is in a state to run the tool.
    guard myAccessPolicy.permits(toolCall) else {
        throw MyAccessPolicyError.denied(toolCall.toolName)
    }
}
.onToolOutput { toolCall, output in
    // Runs after the tool. This is a good place to log any necessary activity.
}
```
Note the **arity**: `onToolCall` closure takes one arg (`toolCall`, which has `.toolName`); `onToolOutput` takes two (`toolCall, output`). But elsewhere `onToolCall { toolCallCount += 1 }` and `.onResponse { ... }` are zero-arg, and `.onResponse { response in print("Debug response: \(response)") }` is one-arg — so these are **overloaded / variadic-arity closures**. `UNVERIFIED` exact signatures.

### 10.7 `@SessionProperty` and `SessionPropertyValues`

```swift
@propertyWrapper struct SessionProperty<Value>     // LanguageModelSession.SessionProperty
final class SessionPropertyValues                  // iOS 27.0+ Beta
protocol SessionPropertyKey : SendableMetatype
@SessionPropertyEntry                              // macro: SessionPropertyEntry()
```
> Use `@SessionProperty` to access session properties from within a `LanguageModelSession.DynamicProfile`, `LanguageModelSession.Profile`, `DynamicInstructions`, and `Tool`.

Built-in property: `\.history`
```swift
var history: ArraySlice<Transcript.Entry> { get set }   // Transcript.history
```
> "The transcript entries **excluding the leading instructions entry**, if present."
> The session history provides the transcript entries after instructions such as prompts, responses, tool calls, and tool outputs. **The history excludes instructions segments from `DynamicInstructions`.**

```swift
// Get a reference to the session history.
@SessionProperty(\.history)
var history

var body: some LanguageModelSession.DynamicProfile {
    Profile {
        Instructions("You are a helpful assistant.")
        TodoWriteTool()
    }
    .onResponse {
        // When the entries exceed `100`, perform a stateful update to the
        // history so it only includes the last `50` entries.
        if history.count > 100 {
            history = history.suffix(50)
        }
    }
}
```
> **NOTE** — Because model output influences the evaluation of `DynamicInstructions` and `Tool`, **the session history is read-only in these contexts.**

Custom session property:
```swift
extension SessionPropertyValues {
    @SessionPropertyEntry
    var activatedSkills: [String: Bool] = [:]
}

struct PlannerTool: Tool {
    let description = "Update the state of the activated skills"

    // Read the shared session state for the currently activated skills.
    @SessionProperty(\.activatedSkills)
    var activatedSkills

    @Generable
    struct Arguments {
        @Guide(description: "The skills to activate")
        var skills: [String]
    }

    func call(arguments: Arguments) -> String {
        // When the model calls this tool, update the skills to an active state.
        for skill in arguments.skills {
            activatedSkills[skill] = true
        }
        return "Activated: \(arguments.skills.joined(separator: ", "))"
    }
}
```
> Note: `PlannerTool` has **no `name`** and `call` is **non-async, non-throwing** — both are legal (defaulted `name`, and `Tool.name-6x7wj` appears in the index as a default implementation).

### 10.8 `DynamicProfileModifier` (reusable trait bundles)
```swift
protocol DynamicProfileModifier          // iOS 27.0+ Beta
func body(content: Content) -> some LanguageModelSession.DynamicProfile
```
```swift
struct DebugProfileModifier: LanguageModelSession.DynamicProfileModifier {
    func body(content: Content) -> some LanguageModelSession.DynamicProfile {
        content
            .temperature(0.0)
            .onResponse { response in
                print("Debug response: \(response)")
            }
    }
}

extension LanguageModelSession.DynamicProfile {
    func debug() -> some LanguageModelSession.DynamicProfile {
        self.modifier(DebugProfileModifier())
    }
}
```
```swift
Profile {
    Instructions("You are a helpful assistant.")
}
.debug()
```

### 10.9 `historyTransform(_:)`
```swift
Profile {
    Instructions("You help people generate fun and interesting book ideas.")
    MyCustomBookTool()
}
.historyTransform { history in
    // Perform a local transformation before prompting the model. This transform
    // doesn't affect the global state of the transcript, so you're not losing
    // existing transcript context.
    Array(history.suffix(20))
}
```
> When a `DynamicProfile` coordinates multiple profiles, `historyTransform(_:)` allows each profile to manage its own view of the history. One profile compresses the history for a small on-device model, and a profile that uses a server model — with a much larger context size — gets the full history.

### 10.10 `DynamicInstructionsForEach`
```swift
struct DynamicInstructionsForEach<Data, ID, Content>
  where Data : RandomAccessCollection, ID : Hashable, Content : DynamicInstructions
```
(SwiftUI-`ForEach`-shaped. Members not documented on the fetched page.)

---

## 11. KV caching (`optimizing-key-value-caching-in-language-model-sessions`)

This article is new in 2026 and is the deepest perf doc in the framework.

> When using a language model session for multi-turn conversations, model providers might maintain a key-value (KV) cache of previously processed tokens... **it's up to the model provider to determine how they manage the cache. How you structure and manage your session determines whether the provider preserves or invalidates that cache.**

Token-sequence layout, verbatim:
> A session typically arranges its content into a token sequence with a specific order, like **instructions appearing at the top, tool definitions coming next, and then transcript entries follow at the end**. Each cached value in the sequence depends on every token that precedes it. When a token changes at any position, the system recomputes the cached values from that point forward.
> Appending new content at the end of the sequence — through calls to respond or stream methods — is a cache-friendly operation... **A change to the instructions, for example, invalidates the cache for the tool definitions and the entire transcript.** A change deep in the transcript, by contrast, only invalidates the values that follow it.

Prewarm guidance, verbatim:
```swift
let session = LanguageModelSession(
    tools: [RecipeDatabaseTool()],
    instructions: """
        You are a helpful cooking assistant. Suggest recipes \
        based on available ingredients and dietary preferences.
        """
)

// Perform a key-value cache computation for the instructions, tools, and the
// provided prefix before sending the person's request.
session.prewarm(
    promptPrefix: "Suggest a recipe using"
)
```
> Prewarming works best when there's time to finish loading the model and caching the prompt before a request. **Prewarm the model when you know usage is at least one or two seconds in the future.**

Tool-mutation accuracy hazards, verbatim:
> Adding or removing tools midsession changes the token sequence at the beginning of the transcript, which invalidates the cached values for all of the entries after that point. When you use `DynamicInstructions`, define the tools you need up front and keep that set unchanged.
> **Removing a tool the model previously used can cause the model to produce unexpected results because it sees references in the transcript for a tool that no longer exists in its tool definitions.** If you do remove any tools, also remove any associated output that refers to them.
> **Adding a new tool late in a conversation can produce unexpected behavior.** The model follows patterns established in earlier turns and might not incorporate a newly available tool into its responses.
> Modifying the transcript impacts model accuracy because **there's no reliable way for the model to distinguish between information that never existed and information that did exist but was removed from the context.** A model treats whatever's in the context as the complete picture and reasons confidently from incomplete evidence.

Ordering rule for DynamicInstructions, verbatim:
> Place instructions and tools that remain constant at the top of your `DynamicInstructions` body, and group conditional content at the bottom. **The framework flattens the resolved instructions and tool definitions in the order you declare them**, so content that appears first in the body occupies earlier positions in the token sequence.
> **NOTE** — Placing the conditional content before the static instructions and tools invalidates the cached values and leads to unnecessary recomputation.

Stateless vs stateful transforms, verbatim:
> **Prefer stateless transforms over stateful ones** because they don't modify the global transcript... A stateless transform that drops entries, like truncating to recent history, invalidates parts of the cache for the entries it removes. However, **a transform that replaces content in-place, like removing debug metadata, can preserve cache consistency** because the model sees the same token sequence each time.

```swift
Profile {
   // The instructions and tools for the profile.
}
.historyTransform { history in
    // Remove debug text from the history. The model sees the same number of
    // entries in the same order so previously cached tokens remain valid.
    clearDebugFromHistory(history)
}
```

Trimming strategy, verbatim:
> **Defer removing entries from the transcript until the context window is nearly full, then consolidate the context in a single operation rather than trimming incrementally after each turn.** Frequent small edits to the middle of the transcript force repeated cache invalidations that increase latency, while a single consolidation step incurs the recomputation cost only once.
> When you do trim, **removing only the most recent entries is cheaper than modifying earlier ones**.

Rehydration:
> The session starts **without a KV cache**, so the model reprocesses the full transcript on the first call to `respond(to:options:)` or `prewarm(promptPrefix:)`... **The reprocessing latency on the first call is proportional to the size of the restored transcript.**
```swift
let transcript = // Load a transcript you save from a previous conversation.
let session = LanguageModelSession(transcript: transcript)
// Begin rebuilding the cache before the person's next prompt arrives --- at
// least one to two seconds in the future.
session.prewarm()
```
> Design your dynamic profiles so transitions between your profiles occur at natural boundaries in the conversation rather than on every turn. **Switching from one profile to another typically changes the entire prefix — which invalidates the cache for the full transcript — so treat it as a deliberate reset.**

---

## 12. Context window management

Source: `/documentation/foundationmodels/managing-the-context-window`

**Hard numbers, verbatim:**
> Apple's on-device foundation model has a context window of **4096 tokens per session**, with a token representing each word, or partial word.
> In Latin alphabet languages such as English, **a token typically represents three to four characters**. For multibyte languages such as **Chinese, Japanese, Korean, and Vietnamese a token typically represents one character**.

(PCC comparison table from the PCC article: `SystemLanguageModel` 4K vs `PrivateCloudComputeLanguageModel` **32K**.)

Everything that consumes budget, verbatim:
> This includes all prompts, instructions, tool definitions and their input and output, generable type schemas, and all of the model's responses.

Instruments workflow, verbatim:
> 1. Choose Product > Profile to launch Instruments.
> 2. Select the **Foundation Models** template, then click Choose.
> 3. Click the Record button and interact with your app's AI features.
> 4. Observe the token count as your app interacts with the model.

Prompt-shortening rules, verbatim:
> - Use imperative verbs that clearly state what you want the model to do: "Generate a story about…," or "List five reasons why…".
> - Provide only the information the model needs for the specific task.
> - Avoid lengthy background information, policies, or unnecessary context.
> - **Reduce prompts to no more than three paragraphs in length.**
> - Eliminate indirect language, excessive formality, and ambiguous jargon.

> **IMPORTANT** — Only use `maximumResponseTokens` to prevent verbose responses. **Limiting tokens can cause the model to generate incomplete or grammatically incorrect responses, like "A cat is a small."**

Recovery pattern:
```swift
do {
    // Perform a request that exceeds the context window.
    let response = try await session.respond(to: prompt)
} catch LanguageModelError.contextSizeExceeded(let context) {
    // Handle exceeding the context window size by creating a new session.
} catch {
    // Handle other errors that are thrown.
}
```
```swift
func newContextualSession(with originalSession: LanguageModelSession) -> LanguageModelSession {
    let allEntries = originalSession.transcript
    let condensedEntries = [allEntries.first, allEntries.last].compactMap { $0 }
    let condensedTranscript = Transcript(entries: condensedEntries)
    let newSession = LanguageModelSession(transcript: condensedTranscript)
    newSession.prewarm()
    return newSession
}
```
> The first transcript entry often contains important instructions and the last entry contains the most recent context. By preserving the first and last entry, you maintain continuity while dramatically reducing token usage.

Chunked-summarization pattern (verbatim, abbreviated):
```swift
let chunks: [String] = // Split a long article into separate chunks.
var chunkSummaries: [String] = []

for (index, chunk) in chunks.enumerated() {
    let session = LanguageModelSession()
    var prompt = """
        Summarize this section of an article:

        \(chunk)
        """
    // Include the previous summary to maintain continuity.
    if index > 0 {
        prompt = """
        Previous section summary: \(chunkSummaries[index - 1])

        \(prompt)
        """
    }
    let response = try await session.respond(to: prompt)
    chunkSummaries.append(response.content)
}

let finalSession = LanguageModelSession()
let combined = chunkSummaries.joined(separator: "\n")
let prompt = """
    Combine these section summaries into one cohesive summary:

    \(combined)
    """
let finalSummary = try await finalSession.respond(to: prompt).content
```

Instruments token knob (from `analyzing-the-runtime-performance-…`):
> Excluding the schema removes redundant schema information and **can save hundreds of tokens per request**.
```swift
do {
    for try await partial in session.streamResponse(to: myPrompt,
                                                    generating: MyCustomItinerary.self,
                                                    includeSchemaInPrompt: false) {
        // Handle the partial result.
    }
} catch {
    // Handle the error that the method throws.
}
```
Instruments privacy warning, verbatim:
> Because a recording **captures and stores all Foundation Models prompts and responses in an unencrypted form**, Instruments presents an alert when you begin recording. The captured data can include sensitive information, so handle trace files accordingly, and use this feature in a manner consistent with the Apple Developer Program License Agreement.

Tokenization cost example, verbatim:
> the word `Sourdough` might be one token, but a phone number like `+1-(408)-555-0123` might use **over ten tokens** because of the characters and symbols.

---

## 13. Multimodal / image input (NEW 2026)

Source: `/documentation/foundationmodels/analyzing-images-with-multimodal-prompting`

### Supported image types, verbatim:
> The framework supports several image types to include in your prompts, like `CGImage`, `CIImage`, `CVPixelBuffer`, and image URLs.
> Use a URL whenever your image comes from a file and verify that it points to an actual image. **The framework infers whether a URL represents an image based on its `UTType`.** If your app captures images or processes video streams, use `CVPixelBuffer`.
> **IMPORTANT** — The framework performs the necessary **scaling and color conversions** before passing an image to the model, so you don't need to scale or convert images to different formats.

### `Attachment`
```swift
struct Attachment<Content>              // iOS 27.0+ Beta
// Conforms: Copyable, Escapable, InstructionsRepresentable, PromptRepresentable
init(_:orientation:)                    // "Creates an attachment from a ..."
init(imageURL:orientation:)             // "Creates an attachment from a file URL pointing to an image."
func label(_:) -> Attachment            // "Assigns a label to an attachment."
```
> Use `Attachment` to include media such as images alongside text in your prompts and instructions.
> Labels help the model identify specific attachments when making tool calls.

```swift
let response = try await session.respond {
    "Describe this image:"
    Attachment(image)
}
```
```swift
Prompt {
    "Compare these two images:"
    Attachment(firstImage)
        .label("image-0")
    Attachment(secondImage)
        .label("image-1")
}
```
```swift
func compareImages(imageOne: CGImage, imageTwo: CGImage) async throws -> String {
    let session = LanguageModelSession()
    let response = try await session.respond {
        "Compare these two images by using three bullet points:"

        Attachment(imageOne)

        // When the image doesn't have a rotation applied, like when you get a
        // image from the `AVFoundation` framework, use orientation to perform
        // a transform before sending it to the model.
        Attachment(imageTwo, orientation: .right)
    }
    return response.content
}
```

### Classification with greedy sampling
```swift
@Generable
enum ImageLabel {
    case cat
    case dog
    case frog
    case bird
}

func classifyImage(_ image: CGImage) async throws -> ImageLabel {
    let session = LanguageModelSession()
    let response = try await session.respond(
        generating: ImageLabel.self,
        options: GenerationOptions(samplingMode: .greedy)
    ) {
        "Choose the label that best represents the following image:"

        Attachment(image)
    }
    return response.content
}
```
> **TIP** — Use the `greedy` sampling option when you want the model to always pick the most likely option; otherwise, the model may select an option that's close.

### Vision framework tools (NEW)
> The Vision framework provides optical character recognition (OCR) and barcode tools that you can add to a session in the Foundation Models framework. Use **`BarcodeReaderTool`** to detect barcodes and interpret their encoded content, and **`OCRTool`** to extract text from images.

```swift
func analyzeBarcodeImage(_ image: CGImage) async {
    do {
        let session = LanguageModelSession(tools: [BarcodeReaderTool()])
        let response = try await session.respond {
            """
            Scan this image for any barcodes. For each barcode found, describe \
            its symbology type and explain what the encoded content means or \
            represents.
            """

            Attachment(image)
                .label("barcode-image")
        }.content

        print("The model response: \(response)")
    } catch {
        // Handle the error.
    }
}
```
Cross-framework note: `OCRTool` and `BarcodeReaderTool` live at `/documentation/Vision/OCRTool` and `/documentation/Vision/BarcodeReaderTool` — **NOT fetched this session**; another agent should harvest the Vision framework updates.

### `ImageReference` — image args in tools
```swift
struct ImageReference                   // iOS 27.0+ Beta, conforms to Generable
var attachmentLabel: String             // "The label of the referenced image."
func resolved(in:) -> Transcript.ImageAttachment?   // current
func resolve(in:)                        // *(Deprecated)*
```
> Use `ImageReference` to allow the model to reference images from the current `LanguageModelSession`'s transcript.

```swift
struct MyTool: Tool {
  @SessionProperty(\.history) var history

  @Generable
  struct Arguments {
    var image: ImageReference
  }

  public func call(arguments: Arguments) async throws -> Output {
    guard let imageAttachment = arguments.image.resolved(in: history) else {
      throw ImageToolError.imageNotFound(arguments.image.attachmentLabel)
    }
    let image = imageAttachment.cgImage
    ...
  }
}
```
Older (deprecated `resolve`) variant from the article, showing you must wrap history in a `Transcript`:
```swift
func call(arguments: Arguments) async throws -> String {
    // Get the image attachment from the session history.
    guard let attachment = arguments.image.resolve(in: Transcript(entries: sessionHistory)) else {
        return "The image isn't in the session history."
    }

    // Perform a classification request on the image to get the top five
    // observations.
    let observations = try await ClassifyImageRequest().perform(on: attachment.ciImage)
    let top = observations.prefix(5)
    return top.map { $0.identifier }.joined(separator: ", ")
}
```
> **Inconsistency:** `resolved(in: history)` takes an `ArraySlice<Transcript.Entry>` while `resolve(in: Transcript(entries:))` takes a `Transcript`. The signature change is likely part of the deprecation. `UNVERIFIED`.

### `Transcript.ImageAttachment`
```swift
struct ImageAttachment                  // iOS 27.0+ Beta, Equatable + Sendable
init(_:orientation:)
init(imageURL:orientation:)
var cgImage                             // "The image as a ..."
var ciImage
var orientation                         // "The display orientation of the image."
var url                                 // "The URL of the original image asset, if the attachment was created from a URL."
func pixelBuffer(resolution:pixelFormat:)  // "Returns the image as a ..., optionally resampled to a given resolution and pixel format."
```

### `ImageAttachmentContent`
```swift
struct ImageAttachmentContent           // iOS 27.0+ Beta — "Holds image data"
```
(No members documented on the fetched page — it is a 1370-byte stub.)

### Prompt engineering for images, verbatim:
> - Describe clearly what you want the model to analyze or extract. Instead of asking, "What's in this image?," try "List all food items in this photo."
> - Consider whether preprocessing is necessary before passing an image to an on-device model, such as isolating a region of interest.
> - Use the `Generable` protocol to constrain responses to specific formats.

Capability gate: `LanguageModelCapabilities.Capability.vision` — "The capability to accept image inputs in prompts."

---

## 14. Private Cloud Compute

Source: `/documentation/foundationmodels/adding-server-side-intelligence-with-private-cloud-compute`

```swift
final class PrivateCloudComputeLanguageModel     // iOS 27.0+ Beta
// Conforms: Copyable, Escapable, LanguageModel, Observable, Sendable, SendableMetatype
init()
var isAvailable: Bool
var availability: PrivateCloudComputeLanguageModel.Availability
var quotaUsage: PrivateCloudComputeLanguageModel.QuotaUsage
var contextSize: Int
var supportedLanguages
func supportsLocale(_:)
```

Capability comparison table, verbatim:

| Capability | `SystemLanguageModel` | `PrivateCloudComputeLanguageModel` |
|---|---|---|
| Preserves privacy | ✅ | ✅ |
| Works offline | ✅ | 🚫 |
| Usage limits | Unlimited | Limit per day |
| Reasoning | Not supported | Multiple levels |
| Context size | 4K | 32K |

> **`SystemLanguageModel` reasoning is "Not supported"** — so `ContextOptions.reasoningLevel` is a PCC-only (or custom-provider-only) knob in practice.

Key quotes:
> The server-based model — accessed through Private Cloud Compute (PCC) — provides a larger **32K-token context size** and stronger reasoning for handling long documents or extended multiturn conversations.
> Typically, you need to handle authentication and manage API keys with server models. **You don't need to handle either when you use PCC.** People just need a device that supports Apple Intelligence and gets a **daily request limit**. People can upgrade their **iCloud+** subscription to get more access when they want it.
> **IMPORTANT** — To develop with PCC you must meet certain **eligibility requirements**. To learn more and request access to the **managed entitlement**, see Accessing Private Cloud Compute (`https://developer.apple.com/private-cloud-compute/`).

Entitlement: **`com.apple.developer.private-cloud-compute`** (`/documentation/BundleResources/Entitlements/com.apple.developer.private-cloud-compute` — not fetched this session).

Recommended adoption order, verbatim:
> Start with the on-device model and evaluate it with the **Evaluations** framework. If you determine your feature needs more reasoning capability or context size, then use PCC.

```swift
// Create a session with the server-side model.
let session = LanguageModelSession(model: PrivateCloudComputeLanguageModel())
let response = try await session.respond(to: "Analyze this document...")
```
```swift
if #available(iOS 27.0, macOS 27.0, watchOS 27.0, visionOS 27.0, *) {
    // Create a session using the server-based model.
} else {
    // Use the on-device model on older versions.
}
```

Availability switch — **note `.systemNotReady`, a PCC-only reason not present on `SystemLanguageModel.Availability.UnavailableReason`**:
```swift
let model = PrivateCloudComputeLanguageModel()

switch model.availability {
case .available:
    // Show your intelligence UI.
case .unavailable(.deviceNotEligible):
    // Show an alternative UI.
case .unavailable(.systemNotReady):
    // PCC isn't ready to serve requests.
case .unavailable(let other):
    // The model is unavailable for an unknown reason.
}
```

### `PrivateCloudComputeLanguageModel.QuotaUsage`
```swift
struct QuotaUsage                        // Sendable
var isLimitReached: Bool
var status: QuotaUsage.Status
var resetDate                            // "The date at which the quota will refresh."
var limitIncreaseSuggestion: QuotaUsage.LimitIncreaseSuggestion?
```
> A quota describes the model's **per-user request budget** and where the caller currently sits relative to it. **Quotas are orthogonal to a model's availability — a model can be available even after its usage limit has been reached.**

```swift
let model = PrivateCloudComputeLanguageModel()

// Depending on the quota state, display a label to keep a person aware
// of the status of their daily limit.
if model.quotaUsage.isLimitReached {
    Text("Usage limit exceeded")
        .foregroundStyle(Color.red)
} else if case .belowLimit(let info) = model.quotaUsage.status {
    if info.isApproachingLimit {
        Text("Nearing usage limit")
            .foregroundStyle(Color.orange)
    }
}

// Display a button in your UI to present the available upgrade options.
if let suggestion = model.quotaUsage.limitIncreaseSuggestion {
    Button("Show options") {
        suggestion.show()
    }
}
```
So `QuotaUsage.Status` has at least `.belowLimit(_:)` with an associated info type exposing `isApproachingLimit`, and `LimitIncreaseSuggestion` has a `show()` method. **Exact `Status` case list UNVERIFIED.**

Quota vs rate limit, verbatim:
> Unlike rate limiting, where a person waits for a period of time before trying again, **exceeding the daily quota means a person either waits for their usage quota to refresh or they upgrade to a higher tier.** Use `resetDate` to inspect when a person's quota refreshes. **This value is empty when the reset date isn't known or when the person is well below their limit.**
> Instead of presenting an alert that a person can dismiss, add UI to clearly communicate the current status of a person's daily usage.

### Xcode simulation of quota states, verbatim:
> 1. Choose **Product > Scheme > Edit Scheme**.
> 2. Select the **Run** page and choose the **Options** tab.
> 3. Select either **"Approaching Quota Usage Limit"** or **"Quota Usage Limit Reached"** from the **"Simulated Apple Foundation Models Availability"** drop-down menu.
> 4. Click Close and run your project.

---

## 15. Custom language model providers (`LanguageModel` protocol)

```swift
protocol LanguageModel : Sendable        // iOS 27.0+ Beta
var capabilities: LanguageModelCapabilities { get }
var executorConfiguration: ...           // "A configuration for an executor capable of running this model."
associatedtype Executor
```
Conforming types shipped by Apple: `PrivateCloudComputeLanguageModel`, `SystemLanguageModel`.

Design guidance, verbatim:
> Implement this protocol to create a bridge between a model and the framework. The protocol describes the capabilities and the configuration for your model. An `Executor` does the work of translating framework types into the types your platform expects, and streams results back through `LanguageModelExecutorGenerationChannel`. **Because most of the work is done in the executor, keep the type that adopts this protocol intentionally light.**
> When your implementation is ready to adopt, **distribute your solution with Swift Package Manager** so developers can easily integrate it into their project.

```swift
// Initialize a session with a custom server model.
let session = LanguageModelSession(model: MyCustomServerLanguageModel())
// Use the same API surface to prompt the model.
let response = try await session.respond(to: "Tell me a joke!")
```

### `LanguageModelCapabilities`
```swift
struct LanguageModelCapabilities         // Sendable
init(_:)                                 // "Specify a list of supported capabilities"
init(capabilities:)                      // *(Deprecated)*
func contains(_:) -> Bool                // "Check if a specific ability is supported."
struct Capability                        // Equatable, Hashable, Sendable
```
`Capability` members (complete):
| Member | Description |
|---|---|
| `guidedGeneration` | "The capability to ensure model output conforms to a given generation schema." |
| `reasoning` | "The capability to reason, structurally separately from producing a response." |
| `toolCalling` | "The capability to call tools to gather information or trigger side effects." |
| `vision` | "The capability to accept image inputs in prompts." |

```swift
struct MyLanguageModel: LanguageModel {
    var capabilities: LanguageModelCapabilities {
        LanguageModelCapabilities([
            .toolCalling,
            .guidedGeneration,
            .reasoning
        ])
    }
}
```
```swift
// Before prompting the model with a generable type, check whether it
// supports guided generation.
if selectedModel.capabilities.contains(.guidedGeneration) {
    let response = try await session.respond(to: "...", generating: MySchema.self)
}
```
> When a model doesn't support a capability, **the framework can refuse to dispatch incompatible requests to the executor** and throw a `LanguageModelError.unsupportedCapability(_:)` error instead.

### `LanguageModelExecutor`
```swift
protocol LanguageModelExecutor : Sendable    // iOS 27.0+ Beta
```
Required shape (from the docs example):
```swift
// Parse generation and context options
func respond(
    to request: LanguageModelExecutorGenerationRequest,
    model: MyLanguageModel,
    streamingInto channel: LanguageModelExecutorGenerationChannel
) async throws {

    // The request includes a sampling set to `greedy`, but your
    // model only uses temperature.
    if request.generationOptions.samplingMode == .greedy {
        // Use the temperature of `0` to approximate the intention.
    }

    // ...
}
```
So `LanguageModelExecutorGenerationRequest` exposes at least `.generationOptions` and `.id: UUID`.

### `LanguageModelExecutorGenerationChannel`
```swift
struct LanguageModelExecutorGenerationChannel   // iOS 27.0+ Beta
await channel.send(...)
```
```swift
func respond(
    to request: LanguageModelExecutorGenerationRequest,
    model: MyLanguageModel,
    streamingInto channel: LanguageModelExecutorGenerationChannel
) async throws {

    let entryID = UUID().uuidString

    // Calculate your total and cached tokens counts for the input.
    let totalTokens = 0
    let cachedTokens = 0

    // Send model identification.
    await channel.send(.response(entryID: entryID, action: .updateMetadata([
        "modelID": "my-model-2026-06-08",
        "requestID": request.id.uuidString
    ])))

    // Report prompt token usage upfront.
    await channel.send(.response(
        entryID: entryID,
        action: .updateUsage(
            input: .init(
                totalTokenCount: totalTokens,
                cachedTokenCount: cachedTokens
            ),
            output: .init(
                totalTokenCount: 0,
                reasoningTokenCount: 0
            )
        )
    ))
}
```
Channel event surface discovered via index-link extraction (all under `/documentation/foundationmodels/languagemodelexecutorgenerationchannel/`):
- `.response(entryID:action:)` where `Response.Action` includes:
  `appendText(_:segmentID:tokenCount:)`, `replaceTextSegment(_:segmentID:tokenCount:)`, `updateMetadata(_:)`, `updateUsage(input:output:)`
- `.reasoning(...)` where `Reasoning.Action` includes:
  `appendText(_:segmentID:tokenCount:)`, `replaceTextSegment(_:segmentID:tokenCount:)`, **`updateSignature(_:tokenCount:)`**
- `.toolCalls(...)` → `ToolCalls.ToolCall.Action.appendArguments(_:tokenCount:)`, `ToolCall.ArgumentsFragment.tokenCount`
- Supporting types: `TextFragment.tokenCount`, `TextSegmentReplacement.tokenCount`, `ReasoningSignature.tokenCount`
- `Usage.Input`: `init(totalTokenCount:cachedTokenCount:)`, `.totalTokenCount`, `.cachedTokenCount`
- `Usage.Output`: `init(totalTokenCount:reasoningTokenCount:)`, `.totalTokenCount`, `.reasoningTokenCount`

**Known open-source implementations of this protocol** (from the June 2026 release notes):
- `CoreAILanguageModel` — https://github.com/apple/coreai-models
- `MLXLanguageModel` — https://github.com/ml-explore/mlx-swift-lm
→ **Cross-link:** these are the bridge between FoundationModels and MLX/Core AI. Other agents covering MLX Swift and Core AI should treat `LanguageModel` + `LanguageModelExecutor` + `LanguageModelExecutorGenerationChannel` as the integration contract.

---

## 16. `Transcript` — full structure

```swift
struct Transcript                        // iOS 26.0+ … watchOS 27.0+ Beta
```
Conforms to the full collection stack: `BidirectionalCollection`, `Collection`, `Copyable`, `Decodable`, `Encodable`, `Equatable`, `Escapable`, **`MutableCollection`**, `RandomAccessCollection`, **`RangeReplaceableCollection`**, `Sendable`, `Sequence`.
```swift
init(entries:)
var history: ArraySlice<Transcript.Entry> { get set }        // iOS 27
var structuredTranscript: StructuredTranscript { get }       // iOS 27
```

### `Transcript.Entry` (enum, iOS 26 + one new case)
| Case | Payload | Description |
|---|---|---|
| `.instructions(_:)` | `Transcript.Instructions` | "Instructions, typically provided by you, the developer." |
| `.prompt(_:)` | `Transcript.Prompt` | "A prompt, typically sourced from an end user." |
| `.response(_:)` | `Transcript.Response` | "A response from the model." |
| **`.reasoning(_:)`** | `Transcript.Reasoning` | "Reasoning from the model." **(NEW iOS 27)** |
| `.toolCalls(_:)` | `Transcript.ToolCalls` | "A tool call containing a tool name and the arguments to invoke it with." |
| `.toolOutput(_:)` | `Transcript.ToolOutput` | "An tool output provided back to the model." |

Conforms: `Copyable`, `CustomStringConvertible`, `Equatable`, `Escapable`, `Identifiable`, `Sendable`.

### `Transcript.Segment` (enum)
| Case | Description |
|---|---|
| `.text(_:)` | "A segment containing text." |
| **`.attachment(_:)`** | "A segment containing an attachment." **(NEW iOS 27)** |
| `.structure(_:)` | "A segment containing structured content." |
| `.custom(_:)` | "A segment containing custom content." |

### Entry payload types
```swift
// Transcript.Instructions
init(id:segments:toolDefinitions:)
var segments, toolDefinitions

// Transcript.Prompt
init(id:segments:options:responseFormat:)                                  // iOS 26
init(id:metadata:segments:options:responseFormat:contextOptions:)          // iOS 27
var id, responseFormat, segments, options, contextOptions, metadata

// Transcript.Reasoning  (iOS 27 only)
init(id:metadata:segments:signature:)
var description, metadata, segments, signature
//   metadata:  "Metadata produced by the model while generating this reasoning entry."
//   segments:  "Ordered reasoning segments."
//   signature: "Opaque producer-supplied signature for this reasoning entry."

// Transcript.Response
init(id:assetIDs:segments:)          // iOS 26
init(id:metadata:segments:)          // iOS 27
var assetIDs, metadata, segments

// Transcript.ToolCall
init(id:toolName:arguments:)         // iOS 26
init(id:metadata:toolName:arguments:)// iOS 27
var arguments, metadata, toolName

// Transcript.ToolCalls
init(id:_:)

// Transcript.ToolOutput
init(id:toolName:segments:)
var id, segments, toolName
```
> **Pattern:** every iOS 27 entry type gained a `metadata` init parameter — this is how custom `LanguageModel` providers thread provider-specific data (see `channel.send(.response(entryID:action:.updateMetadata(...)))`).

### Segment payload types
```swift
// Transcript.TextSegment
init(id:content:)
var content

// Transcript.StructuredSegment
init(id:schemaName:content:)   // older
init(id:source:content:)       // newer
var content, source, schemaName
//   source:     "A source that can be used to understand which type the content represents."
//   schemaName: "A name that can be used to understand which type the content represents."

// Transcript.AttachmentSegment  (iOS 27)
init(id:content:label:)
var content, label

// Transcript.CustomSegment
associatedtype Content
var content, description, id
```

### `Transcript.ResponseFormat`
```swift
init(schema:)
init(type:)
var name
var kind                        // Kind enum with case .schema(_:)
```

### `Transcript.ToolDefinition`
```swift
init(name:description:parameters:)
init(tool:)                     // convenience from a Tool instance
var name, description, parameters
```

### `Transcript.Attachment`
```swift
// enum-ish with case .image(_:)
```

### SwiftUI switch (canonical, verbatim from the `Transcript` page)
```swift
struct HistoryView: View {
    let session: LanguageModelSession

    var body: some View {
        ScrollView {
            ForEach(session.transcript) { entry in
                switch entry {
                case let .instructions(instructions):
                    MyInstructionsView(instructions)
                case let .prompt(prompt):
                    MyPromptView(prompt)
                case let .reasoning(reasoning):
                    MyReasoningView(reasoning)
                case let .toolCalls(toolCalls):
                    MyToolCallsView(toolCalls)
                case let .toolOutput(toolOutput):
                    MyToolOutputView(toolOutput)
                case let .response(response):
                    MyResponseView(response)
                }
            }
        }
    }
}
```
> **Migration footgun:** any exhaustive `switch` over `Transcript.Entry` written for iOS 26 **breaks at compile time on iOS 27** because of the new `.reasoning` case. Same for `Transcript.Segment` and `.attachment`.

---

## 17. Safety

Source: `/documentation/foundationmodels/improving-the-safety-of-generative-model-output`

Two built-in layers, verbatim:
> - Apple Foundation Models, running on-device and on Private Cloud Compute, trained to handle sensitive topics with care.
> - *Guardrails* that aim to block harmful or sensitive content, such as **self-harm, violence, and adult materials**, from both model input and output.
> Because safety risks are often contextual, **some harms might bypass both built-in framework safety layers.**

Guardrail catch:
```swift
do {
    let session = LanguageModelSession()
    let topic = // A potentially harmful topic.
    let prompt = "Write a respectful and funny story about \(topic)."
    let response = try await session.respond(to: prompt)
} catch LanguageModelError.guardrailViolation(let violation) {
    // Handle the safety error.
}
```

Refusals (distinct from guardrails), verbatim:
> When you generate a string response, and the model refuses a request, **it generates a message that begins with a refusal like "Sorry, I can't help with"**.
> **You might not be able to programmatically determine whether a string response is a normal response or a refusal**, so design the experience to anticipate both. If it's critical to determine whether the response is a refusal message, initialize a new `LanguageModelSession` and prompt the model to classify whether the string is a refusal.
> When you use guided generation to generate Swift structures or types, **there's no placeholder for a refusal message. Instead, the model throws** a refusal error.

```swift
do {
    let session = LanguageModelSession()
    let topic = ""  // A sensitive topic.
    let response = try session.respond(
        to: "List five key points about: \(topic)",
        generating: [String].self
    )
} catch LanguageModelSession.GenerationError.refusal(let refusal, _) {
    // Generate an explanation for the refusal.
    if let message = try? await refusal.explanation {
        // Display the refusal message.
    }
}
```
> **Note this snippet is written against the DEPRECATED error type** (`LanguageModelSession.GenerationError.refusal(_:_:)`, two associated values). The iOS 27 equivalent is `LanguageModelError.refusal(_:)` with a single `Refusal` payload. `Refusal.explanation` is `async` and "takes time for the model to generate".

Permissive guardrails, verbatim:
```swift
let model = SystemLanguageModel(guardrails: .permissiveContentTransformations)
```
> **This mode only works for generating a string value.** When you use guided generation, the framework runs the default guardrails against model input and output as usual, and generates `guardrailViolation` and `refusal` errors as usual.
> The session **skips the guardrail checks** in this mode, so it **never throws a `guardrailViolation` error when generating string responses**.
> However, even with the `SystemLanguageModel` guardrails off, the on-device system language model still has a layer of safety. For some content, **the model may still produce a refusal message**.

Named use cases for permissive mode, verbatim:
> - When you want the model to tag the topic of conversations in a chat app when some messages contain profanity.
> - When you want to use the model to explain notes in your study app that discuss sensitive topics.

Prompt-injection warning, verbatim:
> **NOTE** — A session obeys instructions over a prompt, so **don't include input from people or any unverified input in the instructions**. Using unverified input in instructions makes your app **vulnerable to prompt injection attacks**, so write instructions with content you trust.

Instruction technique:
> Use **uppercase words** to emphasize the importance of certain phrases for the model.
```swift
let instructions = """
    Always respond in a respectful way. \
    If someone asks you to generate content that might be sensitive, \
    you must decline with 'Sorry, I can't do that.'
    """
```

Bounded input/output patterns:
```swift
enum TopicOptions {
    case family
    case nature
    case work
}
let topicChoice = TopicOptions.nature
let prompt = """
    Generate a wholesome and empathetic journal prompt that helps \
    this person reflect on \(topicChoice)
    """
```
```swift
@Generable
enum Breakfast {
    case waffles
    case pancakes
    case bagels
    case eggs
}
let session = LanguageModelSession()
let userInput = "I want something sweet."
let prompt = "Pick the ideal breakfast for request: \(userInput)"
let response = try await session.respond(to: prompt, generating: Breakfast.self)
```

Deny list pattern:
```swift
let session = LanguageModelSession()
let userInput = // The input a person enters in the app.
let prompt = "Generate a wholesome story about: \(userInput)"

// A function you create that evaluates whether the input
// contains anything in your deny list.
if verifyText(prompt) {
    let response = try await session.respond(to: prompt)

    // Compare the output to evaluate whether it contains anything in your deny list.
    if verifyText(response.content) {
        return response
    } else {
        // Handle the unsafe output.
    }
} else {
    // Handle the unsafe input.
}
```
> A deny list can be a simple list of strings in your code that you distribute with your app. Alternatively, **you can host a deny list on a server** so your app can download the latest deny list... **avoids requiring a full app update if a safety issue arise.**

Risk assessment table format, verbatim:
> - List each AI feature in your app.
> - For each feature, list possible safety risks that could occur, even if they seem unlikely.
> - For each safety risk, score how serious the harm would be if that thing occurred, from **mild to critical**.
> - For each safety risk, assign a strategy for how you'll mitigate the risk in your app.

Safety-test input categories, verbatim:
> - Input that is nonsensical, snippets of code, or random characters.
> - Input that includes sensitive content.
> - Input that includes controversial topics.
> - Vague or unclear input that could be misinterpreted.

> For each prompt test, **log the timestamp, full input prompt, the model's response, and whether it activates any built-in safety** or mitigations you've included in your app... **To scale your tests, consider using a frontier LLM to auto-grade the safety of each prompt.**

**The single most operationally important safety warning, verbatim:**
> **Apple may update the built-in guardrails at any time outside of the regular OS update cycle.** This is done to rapidly respond, for example, to reported safety concerns that require a fast response. Include all of the prompts you use in your app in your test suite, and run tests regularly to identify when prompts start activating the guardrails.

### `LanguageModelFeedback`
```swift
struct LanguageModelFeedback             // iOS 26.0+ … watchOS 27.0+ Beta
struct LanguageModelFeedback.Issue       // init(category:explanation:)  + Issue.Category
enum LanguageModelFeedback.Sentiment     // .negative, .neutral, .positive  (CaseIterable)
```
```swift
@discardableResult final func logFeedbackAttachment(
    sentiment: LanguageModelFeedback.Sentiment?,
    issues: [LanguageModelFeedback.Issue] = [],
    desiredOutput: Transcript.Entry? = nil) -> Data
```
```swift
let feedbackData = session.logFeedbackAttachment(sentiment: .positive)

let feedbackData = session.logFeedbackAttachment(
    sentiment: .negative,
    issues: [
        LanguageModelFeedback.Issue(
            category: .incorrect,
            explanation: "The model provided outdated information"
        )
    ],
    desiredOutput: Transcript.Entry.response(...)
)
```
Constructing a `desiredOutput`:
```swift
let text = Transcript.TextSegment(content: "The capital of France is Paris.")
let segment = Transcript.Segment.text(text)
let response = Transcript.Response(segments: [segment])
let entry = Transcript.Entry.response(response)
```
```swift
let customType = MyCustomType(...) // A generable type.
let structure = Transcript.StructuredSegment(schemaName: String(describing: Foo.self), content: customType.generatedContent)
let segment = Transcript.Segment.structure(structure)
let response = Transcript.Response(segments: [segment])
let entry = Transcript.Entry.response(response)
```
Concatenating and saving (the returned `Data` is JSON):
```swift
let allFeedback = feedbackData + feedbackData2 + feedbackData3
let url = URL(fileURLWithPath: "path/to/save/feedback.json")
try allFeedback.write(to: url)
```
> Use `LanguageModelFeedback` to retrieve language model session transcripts from people using your app. After collecting feedback, you can **serialize it into a JSON file and include it in the report you send with Feedback Assistant**.
> Only `Issue.Category.incorrect` is confirmed by example; the full category list is `UNVERIFIED`.

---

## 18. Prompting + model versioning (short notes)

Source: `/documentation/foundationmodels/prompting-an-on-device-foundation-model`

> Many prompting techniques are designed for server-based "frontier" foundation models, because they have a larger context window and thinking capabilities. However, **when prompting an on-device model, your prompt engineering technique is even more critical because the model you access is much smaller.**

Techniques list, verbatim:
> - Use simple, clear instructions
> - Iterate and improve your prompt based on the output you receive in testing
> - **Provide the model with a reasoning field before answering a prompt**
> - Reduce the thinking the model needs to do
> - Split complex prompts into a series of simpler requests
> - Add "logic" to conditional prompts with "if-else" statements
> - Leverage shot-based prompting — such as one-shot, few-shot, or zero-shot prompts

Do/Don't table (partial, verbatim):
| ✅ Prompting strategies to use | 🚫 Prompting strategies to avoid |
|---|---|
| Focus on a single, well-defined goal | Combining multiple unrelated requests |
| Be direct with imperative verbs like "List" or "Create" | Unnecess… *(truncated in harvest)* |

Conditional prompt example, verbatim: *"If it's a question, answer it directly. If it's a statement, ask a follow-up question."*

### Capability tables (from `generating-content-and-performing-tasks-with-foundation-models`)

**Supported**, verbatim:
| Capability | Prompt example |
|---|---|
| Summarize | "Summarize this article." |
| Extract entities | "List the people and places mentioned in this text." |
| Understand text | "What happens to the dog in this story?" |
| Refine or edit text | "Change this story to be in second person." |
| Classify or judge text | "Is this text relevant to the topic 'Swift'?" |
| Compose creative writing | "Generate a short bedtime story about a fox." |
| Generate tags from text | "Provide two tags that describe the main topics of this text." |
| Generate game dialog | "Respond in the voice of a friendly inn keeper." |

**AVOID**, verbatim:
| Capabilities to avoid | Prompt example |
|---|---|
| Do basic math | "How many b's are there in bagel?" |
| Create code | "Generate a Swift navigation list." |
| Perform logical reasoning | "If I'm at Apple Park facing Canada, what direction is Texas?" |

> Note: the letter-counting example in the Evaluations docs is literally the "avoid" case — Apple uses it to demonstrate that **tool calling lifts Exact Match from 58% → 100%** on that task.

### Model-version gating (`updating-prompts-for-new-model-versions`)
```swift
if #available(iOS 26.4, macOS 26.4, visionOS 26.4, *) {
    // Use the prompt that you update for the the latest system version.
} else {
    // Use the prompt for the model in 26.0 to 26.3.
}
```
```swift
if #available(iOS 26.4, macOS 26.4, visionOS 26.4, *) {
    return String(localized: "support-ticket-summarizer-v1.1", table: "Prompts")
} else {
    return String(localized: "support-ticket-summarizer-v1.0", table: "Prompts")
}
```
> Order the availability attribute from the newest version to the oldest version... **The availability of the Foundation Models framework starts at 26.0, so you don't need to check for versions prior to that.**
> Because the older model is only included as part of the beta program, **it's essential to produce a record of what output your prompt produces with the prior model.**

### Multilingual (`supporting-languages-and-locales-with-foundation-models`)
> The on-device system language model is **multilingual** — the same model understands and generates text in any language that Apple Intelligence supports.
> In the code below, ***all* inputs need to be in supported language for the model to understand, including all `Generable` types and descriptions.**
> Because the framework treats `Generable` types as model inputs, **the names of properties like `age` or `profile` are just as important as the `@Guide` descriptions** for helping the model understand your request.
> People can use the Settings app on their device to configure **the language they prefer to use on a per-app basis**, which might differ from their default language.
> Keep in mind that **language support improves over time in newer model and OS versions.** Thus, someone using your app with an older OS may not have the latest language support.

```swift
@Generable(description: "Basic profile information about a cat")
struct CatProfile {
    var name: String

    @Guide(description: "The age of the cat", .range(0...20))
    var age: Int

    @Guide(description: "One sentence about this cat's personality")
    var profile: String
}

#Playground {
    let response = try await LanguageModelSession().respond(
        to: "Generate a rescue cat",
        generating: CatProfile.self
    )
}
```
Reference for the supported-language list: *"the 'Supported languages' section in How to get Apple Intelligence"* → `https://support.apple.com/en-us/121115`.

---

## 19. EVALUATIONS FRAMEWORK

**Framework path: `/documentation/evaluations` — confirmed to exist (44 KB index, HTTP 200).**
Everything in this framework is `iOS 27.0+ Beta, iPadOS 27.0+ Beta, Mac Catalyst 27.0+ Beta, macOS 27.0+ Beta, visionOS 27.0+ Beta, watchOS 27.0+ Beta` and tagged **Beta** on the index. Swift module name is `Evaluations` (`import Evaluations`).

Four-step mental model, verbatim from `evaluating-language-model-responses`:
> - Provide input as a dataset of samples with expected outputs.
> - Define the subject, the intelligence-powered feature you are testing.
> - Add evaluators that score each response against metrics you define.
> - Aggregate those scores into a metric summary you compare across runs.

Framing quote:
> Evaluations replace manual spot checks with structured, repeatable measurements of your model's output quality... Because you define your metrics before tuning prompts or switching models, **every change is measured against the same criteria.**

### 19.1 Full symbol inventory (top level)
`AggregateMetric`, `AggregationOperation`, `ArgumentMatcher`, `ArgumentValue`, `ArrayLoader`, `Evaluation`, `EvaluationContext`, `EvaluationError`, `EvaluationResult`, `EvaluationResultsError`, `EvaluationSubject`, `EvaluationTrait`, `Evaluator`, `EvaluatorError`, `EvaluatorProtocol`, `EvaluatorsBuilder`, `JSONLoader`, `Loader`, `Metric`, `MetricsAggregator`, `ModelJudgeError`, `ModelJudgeEvaluator`, `ModelJudgePrompt`, `ModelSample`, `ModelSampleInput`, `ModelSampleOutput`, `ModelSampleProtocol`, `ModelSubject`, `ResultColumn`, `SampleGenerator`, `SampleProtocol`, `ScaleOption`, `ScoreDimension`, `ScoreLevel`, `ScoringMode`, `ScoringScale`, `StreamLoader`, `StructuredTranscript`, `StructuredValue`, `SubjectInferenceError`, `ToolCallEvaluator`, `ToolExpectation`, `TrajectoryExpectation`.

Articles: `designing-effective-evaluations`, `designing-effective-model-judges`, `designing-evaluation-criteria` (titled "Designing specific, measurable criteria in an evaluation suite"), `designing-evaluation-datasets` ("Designing datasets to test your feature"), `evaluating-language-model-responses`, `evaluating-tool-calling-behavior`, `generating-synthetic-evaluation-datasets` ("Generating synthetic datasets"), `scoring-with-model-as-judge-evaluators`.
Sample code: `book-tracker-using-evaluations-to-evaluate-an-intelligent-feature` (**Book Tracker**, 31 KB page — the flagship sample).

### 19.2 `Evaluation` protocol
```swift
protocol Evaluation : Sendable
```
Requirements:
```swift
associatedtype Sample                     // "The type of input samples in the evaluation dataset."
associatedtype SampleLoader               // "The type of the sample loader used to provide the evaluation dataset."
var dataset: Self.SampleLoader { get }

associatedtype Subject                    // "The type of the subject produced by the system under test."
func subject(from sample: Self.Sample) async throws -> Self.Subject

var name: String { get }                  // "The default name, derived from the type name."
var evaluators: Self.Evaluators { get }
typealias Evaluators                      // "Shorthand for the evaluator array type, resolved per-conformance."
func aggregateMetrics(using aggregator: inout MetricsAggregator)

func run(info:)                           // "Runs the evaluation against the dataset and computes metric results."
var inputColumn: ResultColumn<...>        // typed DataFrame column descriptors
var responseColumn: ResultColumn<...>
var expectedColumn: ResultColumn<...>
```

Canonical minimal conformance (verbatim):
```swift
struct MyEvaluation: Evaluation {
    let metric = Metric("Match")

    let dataset = ArrayLoader(samples: [
        ModelSample(prompt: "One plus one is...", expected: "Two.")
    ])

    func subject(from sample: ModelSample<String>) async throws -> ModelSubject<String> {
        ModelSubject(value: "Two.")
    }

    var evaluators: Evaluators {
        Evaluator { sample, subject in
            let metric = Metric("Match")
            guard let expected = sample.expected else { return metric.ignore() }
            return subject.value == expected ? metric.passing() : metric.failing()
        }
    }

    func aggregateMetrics(using aggregator: inout MetricsAggregator) {
        aggregator.computeMean(of: metric)
    }
}
```

### 19.3 Samples and loaders
```swift
struct ModelSample<ExpectedValue> where ExpectedValue : Decodable, Encodable, Sendable
// Conforms: ModelSampleProtocol, SampleProtocol, Codable, Sendable
init(prompt:expected:instructions:generationSchema:expectations:)     // String-based
init(prompt:expected:instructions:generationSchema:expectations:)     // FoundationModels `Prompt`-based overload
init(input:expected:expectations:)                                    // prebuilt ModelSampleInput
var prompt, promptDescription, instructions, instructionsDescription, input
var expected, output
var expectations                          // "The expected pattern of tool calls for this sample."
var generationSchema                      // "The output schema for the model's response."
```
> Accepts string-based prompts and instructions. **For multimodal prompts, create a custom `ModelSampleProtocol` conformance or use the `init(input:expected:expectations:)` initializer with a prebuilt `ModelSampleInput`.**

```swift
struct ArrayLoader<Sample> where Sample : SampleProtocol       // init(samples:)
struct JSONLoader<Sample> where Sample : SampleProtocol        // init(url:)
struct StreamLoader                                             // (not fetched)
protocol Loader
```
`JSONLoader` format detection, verbatim:
> - If the first non-whitespace character is `[`, the file is treated as a **JSON array** (`[{...}, {...}]`) and decoded in one pass.
> - Otherwise, the file is treated as **JSONL** (JSON Lines), where each non-empty line is decoded as an individual sample.
> **Malformed entries are logged via `OSLog` and skipped.** A failure to open the file propagates as a thrown error.

### 19.4 Subjects
```swift
protocol EvaluationSubject                // associatedtype Value; var value: Self.Value
struct ModelSubject                       // "The subject type for language model evaluations."
init(value: Value, transcript: StructuredTranscript?)
var value: Value
var transcript: StructuredTranscript?
var toolCalls: [Transcript.ToolCall]
```
```swift
struct StructuredTranscript
init(toolCalls: [Transcript.ToolCall],
     toolOutputs: [Transcript.ToolOutput],
     instructionText: String,
     prompts: [String],
     responses: [Transcript.Response])
var instructionText: String
var prompts: [String]
var responses: [Transcript.Response]
var toolCalls: [Transcript.ToolCall]
var toolOutputs: [Transcript.ToolOutput]
```
Bridge from FoundationModels: `Transcript.structuredTranscript` (iOS 27) returns this type.

```swift
enum StructuredValue                      // "A type-safe representation of JSON values."
case string(String)
case int(Int)
case double(Double)
case bool(Bool)
case null
case array([StructuredValue])
case dictionary([String : StructuredValue])
var value: Any
```

Canonical `subject(from:)`:
```swift
func subject(from sample: ModelSample<Int>) async throws -> ModelSubject<Int> {
    // Create the language model session; you can customize this with instructions and you can
    // choose the model you want to use.
    let session = LanguageModelSession()
    // Create the model response the same way you do in your app.
    let response = try await session.respond(to: sample.prompt, generating: Int.self)
    // Return the model's response along with the transcript.
    return ModelSubject(
        value: response.content,
        transcript: session.transcript.structuredTranscript
    )
}
```

### 19.5 Metrics
```swift
struct Metric                             // Copyable, CustomStringConvertible, Equatable, Sendable
init(_ name: String)
func passing(rationale:) -> Metric
func failing(rationale:) -> Metric
func scoring(_:rationale:) -> Metric
func ignore(rationale:) -> Metric         // "excluded from aggregation"
var name: String                          // "used as the DataFrame column name"
var value: Metric.Value
var doubleValue                           // "or ... for ignored metrics"
var rationale: String?
enum Metric.Value                         // includes .passing / .failing (seen in code: `scores[row]?.value == .failing`)
```
> The factory methods (`passing`, `failing`, `scoring`, `ignore`) **return a new `Metric` with the result stored inside.**
> **Design note:** a `Metric` is both the *identifier* and the *result carrier*. `let m = Metric("Accuracy")` declared as a stored property is the identifier; `m.passing()` is what an evaluator returns.

```swift
let metric = Metric("Accuracy")
let result = metric.passing(rationale: "Exact match")
```

### 19.6 Evaluators
```swift
protocol EvaluatorProtocol<Input, Subject> : Sendable
associatedtype Input
associatedtype Subject
func metrics(subject: Self.Subject, input: Self.Input) async throws -> [Metric]
```
```swift
struct Evaluator<Input>
  where Input : SampleProtocol,
        Input.ExpectedValue : Decodable, Input.ExpectedValue : Encodable, Input.ExpectedValue : Sendable
```
```swift
Evaluator { sample, subject in
    let metric = Metric("TitleMatch")
    guard let expected = sample.expected else { return metric.ignore() }
    return subject.value == expected ? metric.passing() : metric.failing()
}
```
Custom evaluator conformance:
```swift
struct MyEvaluator<Input: SampleProtocol>: EvaluatorProtocol
where Input.ExpectedValue: Sendable & Codable {
    let metric = Metric("Quality")

    func metrics(
        subject: ModelSubject<Input.ExpectedValue>,
        input: Input
    ) async throws -> [Metric] {
        return [metric.scoring(1.0)]
    }
}
```
Result builder:
```swift
@resultBuilder EvaluatorsBuilder
static func buildBlock(any EvaluatorProtocol<Sample, Subject>...) -> [any EvaluatorProtocol<Sample, Subject>]
static func buildExpression(any EvaluatorProtocol<Sample, Subject>) -> any EvaluatorProtocol<Sample, Subject>
static func buildOptional([any EvaluatorProtocol<Sample, Subject>]?) -> [any EvaluatorProtocol<Sample, Subject>]
```
> `buildOptional` exists but **no `buildEither`** is listed — so `if/else` in an `evaluators` block is likely unsupported; only bare `if`. `UNVERIFIED`.

Errors: `EvaluationError`, `EvaluatorError` ("A typed reason why an evaluator failed while scoring a produced subject"), `SubjectInferenceError` ("A typed reason why `subject(from:)` failed to produce a subject for a sample"), `EvaluationResultsError`, `ModelJudgeError`.

### 19.7 `MetricsAggregator`
```swift
struct MetricsAggregator
func computeMean(of:)
func computeMedian(of:)
func computeMode(of:)
func computeMinimum(of:)
func computeMaximum(of:)
func computeStandardDeviation(of:)
func computeVariance(of:)
func custom(of:label:_:)                 // "Computes a custom aggregation from a single metric's results."
func group(_:_:)                         // "Creates a group of related metrics."
struct MetricsAggregator.Group
```
```swift
let accuracy = Metric("Accuracy")

func aggregateMetrics(using aggregator: inout MetricsAggregator) {
    aggregator.computeMean(of: accuracy)
    aggregator.computeMaximum(of: accuracy)
    aggregator.computeStandardDeviation(of: accuracy)
}
```
```swift
func aggregateMetrics(using aggregator: inout MetricsAggregator) {
    // Create a group called "Accuracy" with the mean of ExactMatch.
    aggregator.group("Accuracy") { group in
        group.computeMean(of: exactMatch)
    }
    // Create a group called "Error" with the maximum AbsoluteError.
    aggregator.group("Error") { group in
        group.computeMaximum(of: absoluteError)
    }
}
```
Supporting: `AggregateMetric` ("An aggregate statistic computed from a metric's results across the evaluation dataset"), `AggregationOperation` ("The type of aggregation operation used to compute a summary statistic") — used as `.mean(of: metric)` at read time.

### 19.8 Running: Swift Testing integration
```swift
struct EvaluationTrait          // conforms to Testing.TestScoping, Testing.TestTrait, Testing.Trait
// "A test trait that runs an evaluation and records the result as attachments."
struct EvaluationContext
static var current: EvaluationContext
let result: EvaluationResult
```
```swift
import Testing
import Evaluations

struct LetterCountTests {
    static let evaluation = LetterCountEvaluation()

    @Test(.evaluates(Self.evaluation))
    func letterCounting() async throws {
        let result = EvaluationContext.current.result
        let score = result.aggregateValue(.mean(of: Self.evaluation.exactMatch))
        #expect(score > 0.8)
    }
}
```
> The trait spelling is **`.evaluates(_:)`** (an `EvaluationTrait` factory). Viewing results:
> "When the run finishes, open the **Report navigator** and select the **Evaluations** item beneath the test run to open the evaluation report."
> "For a side-by-side view, choose **Compare** and select a run for each side."

### 19.9 `EvaluationResult`
```swift
struct EvaluationResult                   // Sendable
var summary: DataFrame                    // "Aggregated statistics for each metric in the evaluation."
var detailed: DataFrame                   // "Individual results for each sample in the evaluation."
let evaluationInfo: [String : String]     // "such as the model name, prompt version, or dataset"
let evaluationID: String
let resultID: UUID
var reportMetadata: [String : any Sendable]
func aggregateValue(_ op: AggregationOperation) -> Double
var startTime, endTime, duration
var groupedSummary                        // "A formatted description of summary metrics organized by groups."
func jsonRepresentableDataFrame(of:)
func saveJSON(to:includeReportMetadata:)
func jsonData(includeReportMetadata:jsonOptions:)
static func loadJSON(from:)
static func loadJSONLines(from:)          // "Loads an array of evaluation results from a JSONL file on disk."
init(jsonData:)
enum EvaluationResult.DataFrameKind
struct ResultColumn
```
> `summary` and `detailed` are **TabularData `DataFrame`s** — cross-link to the TabularData framework.

Typed column reads:
```swift
@Test(.evaluates(Self.evaluation))
func inspectDetailedResults() async throws {
    let result = EvaluationContext.current.result

    // Read typed columns out of the per-sample DataFrame.
    let inputs   = result.detailed[Self.evaluation.inputColumn]
    let expected = result.detailed[Self.evaluation.expectedColumn]
    let scores   = result.detailed[metric: Self.evaluation.exactMatch]

    // Surface the prompts where the model's count disagreed with the expected count.
    for row in 0..<scores.count where scores[row]?.value == .failing {
        let prompt = inputs[row]?.promptDescription ?? "<missing>"
        let target = expected[row].map(String.init) ?? "?"
        print("Missed (expected \(target)): \(prompt)")
    }

    #expect(scores.count == 5)
}
```
> Note the **two subscript forms**: `detailed[someResultColumn]` and `detailed[metric: someMetric]`.

### 19.10 Tool-call evaluation
```swift
struct ToolCallEvaluator<Input>
  where Input : ModelSampleProtocol, Input.Expectation == TrajectoryExpectation
init(allPass:percentagePass:)             // both are Metric values
```
```swift
let toolsAllPass = Metric("Tools All Pass")
let toolsPercentagePass = Metric("Tools Percentage Pass")

let evaluator = ToolCallEvaluator<ModelSample<String>>(
    allPass: toolsAllPass, percentagePass: toolsPercentagePass
)
```

```swift
struct TrajectoryExpectation
init(ordered:)
init(ordered:allowsAdditionalToolCalls:)
init(ordered:unordered:disallowed:)
init(expected:arguments:)                 // single-tool convenience
```
All four forms, verbatim from the docs:
```swift
TrajectoryExpectation(ordered: [
    ToolExpectation("authenticate"),
    ToolExpectation("processResults"),
])
```
```swift
TrajectoryExpectation(ordered: [
    ToolExpectation("authenticate"),
    .anyOrder([
        ToolExpectation("fetchData"),
        ToolExpectation("fetchMetadata"),
    ]),
    ToolExpectation("processResults"),
], allowsAdditionalToolCalls: false)
```
```swift
TrajectoryExpectation(
    ordered: [
        ToolExpectation("findActivities"),
        ToolExpectation("estimateTravelTime"),
    ],
    unordered: [ToolExpectation("getWeather")],
    disallowed: [ToolExpectation("deleteData")]
)
```
```swift
TrajectoryExpectation(expected: "getWeather", arguments: [
    .exact(argumentName: "location", value: "Paris, France")
])
```

```swift
struct ToolExpectation                    // conforms to Generable(!)
init(_ name: String, arguments: [ArgumentMatcher])
static func anyOrder(_:) -> ToolExpectation
var name, arguments, isAnyOrderGroup
```
> "For ordered sequences where multiple tools must all be called at the same position but their relative order doesn't matter, use `anyOrder(_:)`."
> `ToolExpectation` and `ArgumentMatcher` both conform to **`Generable`** — which is how `.naturalLanguage` matching is fed to a judge model.

### `ArgumentMatcher` — complete table (verbatim from Apple)
```swift
enum ArgumentMatcher                      // Generable, Codable, Sendable
```
| Validation Strategy | Rules |
|---|---|
| `.exact(argumentName:value:)` | "Value must equal the expected value exactly. Use for identifiers, enum values, and precise inputs." |
| `.keyOnly(argumentName:)` | "Argument must be present with any value. Use when you care that the model provides the parameter but any value is acceptable." |
| `.oneOf(argumentName:allowedValues:)` | "Value must be one of the allowed options. Use for ambiguous prompts with multiple valid interpretations." |
| `.range(argumentName:minimum:maximum:)` | "Numeric value must fall within bounds (inclusive). Use for quantities where a range is acceptable." |
| `.pattern(argumentName:regex:)` | "String must match a regular expression. Use for structured formats: emails, dates, IDs." |
| `.contains(argumentName:substring:)` | "String must contain a substring. Use when the argument references a concept but phrasing varies." |
| `.hasPrefix(argumentName:prefix:)` | "String must start with a prefix. Use for paths, URLs, or namespaced values." |
| `.hasSuffix(argumentName:suffix:)` | "String must end with a suffix. Use for file extensions or domain-specific endings." |
| `.naturalLanguage(argumentName:criteria:)` | "**A language model judges whether the value satisfies the criteria.** Use when correctness is subjective or hard to express with string operations, for example, validating that a query argument is 'a weather-related question'." |

```swift
let matchers: [ArgumentMatcher] = [
    .exact(argumentName: "city", value: "San Francisco"),
    .keyOnly(argumentName: "units"),
    .naturalLanguage(argumentName: "prompt", criteria: "A weather-related question")
]
```
Supporting: `ArgumentValue` ("A primitive value type for argument specifications that is @Generable").
> **Value-type footgun:** the docs show `.exact(argumentName: "location", value: "Paris, France")` (bare string) in one place and `.exact(argumentName: "letter", value: .string("r"))` (`ArgumentValue`/`StructuredValue` case) in another. Both presumably work via `ExpressibleByStringLiteral`. `UNVERIFIED`.

Full worked example (verbatim, from `evaluating-language-model-responses`):
```swift
// Create a tool that conforms to the Tool protocol and supports letter counting.
struct CountLetterOccurrences: Tool {
    let name = "count_letters"
    let description = "Counts how many times a letter appears in a word."

    // The tool needs two arguments: the letter you want to count and the word.
    @Generable
    struct Arguments {
        @Guide(description: "The letter to count")
        var letter: String
        @Guide(description: "The word")
        var word: String
    }

    // The letter counting tool's implementation.
    func call(arguments: Arguments) async throws -> Int {
        return arguments.word.lowercased().filter { String($0) == arguments.letter.lowercased() }.count
    }
}
```
```swift
ModelSample(
    prompt: "Count the letter 'r' in 'strawberry'.",
    expected: 3,
    // Attach a trajectory expectation that defines the expected tool-calling sequence.
    expectations: TrajectoryExpectation(
        ordered: [
            // Expect the model to call `count_letters` with these exact arguments.
            ToolExpectation(
                "count_letters",
                arguments: [
                    .exact(argumentName: "letter", value: .string("r")),
                    .exact(argumentName: "word", value: .string("strawberry")),
                ]
            ),
        ]
    )
),
```
```swift
// Computed metrics.
let exactMatch = Metric("ExactMatch")
let absoluteError = Metric("AbsoluteError")
// Tool calling metrics.
let toolsAllPass = Metric("ToolsAllPass")
let toolsPercentagePass = Metric("ToolsPercentagePass")

var evaluators: Evaluators {
    // Score tool calls against the trajectory expectations defined on each sample.
    ToolCallEvaluator(allPass: toolsAllPass, percentagePass: toolsPercentagePass)
    // Also check whether the final output matches the expected answer.
    Evaluator { input, subject in
        guard let expected = input.expected else { return exactMatch.ignore() }
        return subject.value == expected ? exactMatch.passing() : exactMatch.failing()
    }
}
```
Reported result (from the doc's figure captions): **LetterCountEvaluation Exact Match 58%** without the tool vs **LetterCountEvaluationTools 100%** with it, across **12 responses**.

Evaluation-vs-behavior note, verbatim:
> Tool-calling evaluation measures **whether the model selects the right tool with the right arguments, not what the tool does when called**. Your tools don't need to perform real actions during evaluation, so simple stubs like this one work well.

### 19.11 Model-as-judge
```swift
struct ModelJudgeEvaluator<Input> where Input : ModelSampleProtocol
// Conforms: EvaluatorProtocol, Sendable

// single-dimension
init(_:scale:judge:scoringMode:)
init(_:scale:judge:scoringMode:prompt:)
// multi-dimension
init(judge:dimensions:scoringMode:)
init(judge:dimensions:scoringMode:prompt:)
// pairwise
static func pairwise(_:scale:judge:scoringMode:evaluationTarget:)
static func pairwise(judge:dimensions:scoringMode:evaluationTarget:)

static var defaultInstructions: String    // "The default system instructions the model uses when no custom instructions are provided."
func judgePrompt(for:output:)             // "Builds and returns the full judge prompt for inspection, debugging, or logging."
var dimensions, scoringMode
enum/struct ScoringMode                   // "The scoring constraint mode for a model-as-judge evaluator."
```
> `ModelJudgeEvaluator` sends the query, response, and optional reference data to a judge model, which returns scores for one or more dimensions. **The response is automatically serialized as JSON**, because `OutputType` is `Codable`, or is customizable via `ModelJudgePrompt`.

```swift
struct ModelJudgePrompt<Input> where Input : ModelSampleProtocol
init(instructions:evaluationTarget:reference:)
static var defaultInstructions
var instructions: String                  // "The system instructions for the judge model."
var evaluationTarget                      // closure: response -> String for the judge prompt
var reference                             // closure: (input, response) -> [String: String] labeled sections
```
> Pairwise evaluation **builds its own prompt internally**. The `instructions` and `reference` components **only apply to pointwise evaluators.** Pairwise evaluation supports `evaluationTarget` through its own parameter.
> If you omit the `ModelJudgePrompt` entirely, the evaluator uses default instructions that ask the model as judge to rate the response using the scoring scale.

```swift
struct ScoringScale                       // Sendable
static func numeric(_:)                   // [Double: String] level -> description
static func passFail(passDescription:failDescription:)
static func custom(_:)                    // a ScoreLevel-conforming enum type
init(options:)
var options                               // "ordered from highest to lowest value"
struct ScaleOption
protocol ScoreLevel                       // requires: var guideDescription: String; var value: Double
```
```swift
// Numeric scale
let _ = ScoringScale.numeric([5: "Flawless", 3: "Readable", 1: "Incomprehensible"])

// Pass/fail
let _ = ScoringScale.passFail(passDescription: "Safe", failDescription: "Unsafe")

// Typed enum
enum SafetyLevel: ScoreLevel {
    case safe, unsafe
    var guideDescription: String { self == .safe ? "Safe" : "Unsafe" }
    var value: Double { self == .safe ? 1 : 0 }
}
let _ = ScoringScale.custom(SafetyLevel.self)
```

```swift
struct ScoreDimension                     // Sendable
init(_:description:scale:)
var name                                  // "used as the DataFrame column name"
var metric: Metric                        // "A metric identifier derived from this dimension's name."
var scale: ScoringScale
var description: String?
```
```swift
ScoreDimension("Grammar", scale: .numeric([
    5: "Flawless grammar throughout",
    3: "Some errors but generally readable",
    1: "Pervasive errors making text difficult to understand"
]))
```
```swift
ScoreDimension("Safe", scale: .passFail(
    passDescription: "The response is safe and appropriate",
    failDescription: "The response contains harmful content"
))
```

Single-dimension judge, verbatim:
```swift
var evaluators: Evaluators {
    ModelJudgeEvaluator(
        "HaikuQuality",
        scale: .numeric([
            4: "Excellent - Perfect 5-7-5 form, strongly relevant to the topic, and uses vivid imagery that evokes emotion.",
            3: "Good - Correct or near-correct form, clearly relevant, with some evocative language.",
            2: "Poor - Incorrect syllable count, weak connection to topic, or lacks poetic quality.",
            1: "Very poor - Not recognizable as a haiku, off-topic, or incoherent.",
        ]),
        judge: SystemLanguageModel.default,
        prompt: ModelJudgePrompt(
            instructions: """
                You are an expert poetry evaluator. Evaluate the quality of AI-generated haiku poems \
                considering: form (traditional 5-7-5 syllable structure), relevance (clearly relates to \
                the given topic), and imagery (vivid, sensory language that evokes a feeling). \
                Give step-by-step explanations for your scoring.
                """
        )
    )
}
```
> **`judge:` takes any `LanguageModel`** — `SystemLanguageModel.default` in every example, but `PrivateCloudComputeLanguageModel()` should work. `UNVERIFIED`.

Multi-dimension (scores all dimensions in ONE judge call):
```swift
private let accuracy = ScoreDimension(
    "Accuracy",
    description: "Does each tag describe the book itself?",
    scale: .numeric([
        4: "Every tag describes the book's genre, themes, or setting.",
        3: "Most tags describe the book but one or two reflect the reader's opinion.",
        2: "Some tags describe the book but most reflect the reader's opinion.",
        1: "None of the tags meaningfully describe the book.",
    ])
)
private let usefulness = ScoreDimension(
    "Usefulness",
    description: "Is each tag the right level for browsing a personal library?",
    scale: .numeric([
        4: "Every tag would help someone find this book while browsing.",
        3: "Most tags are useful for browsing but a couple are too narrow or generic.",
        2: "About half the tags are useful; the rest are too narrow or generic.",
        1: "The tags would not help someone browse a library.",
    ])
)

var evaluators: Evaluators {
    ModelJudgeEvaluator(
        dimensions: [accuracy, usefulness]
    )
}
```
> The evaluator scores all dimensions in a single call to the model as judge, **so you get multiple metrics without extra latency.**
```swift
func aggregateMetrics(using aggregator: inout MetricsAggregator) {
    aggregator.group("Judge") { group in
        group.computeMean(of: accuracy.metric)
        group.computeMean(of: usefulness.metric)
    }
}
```

Formatting + reference closures:
```swift
prompt: ModelJudgePrompt(
    evaluationTarget: { value in
        "\(value.tags.count) tags: " + value.tags.joined(separator: ", ")
    }
)
```
```swift
prompt: ModelJudgePrompt(
    instructions: """...""",
    evaluationTarget: { value in
        "\(value.tags.count) Generated tags: " + value.tags.joined(separator: ", ")
    },
    reference: { input, _ in
        guard let expected = input.expected else { return [:] }
        return ["Expected Tags": expected.tags.joined(separator: ", ")]
    }
)
```
> By default, the model as judge receives a **JSON serialized** version of the result.
> The `reference` closure receives the input sample and the model's response, and returns a `[String: String]` dictionary. **Each key-value pair becomes a labeled section in the judge's prompt.**

Pairwise:
```swift
var evaluators: Evaluators {
    ModelJudgeEvaluator.pairwise(
        "ExplanationComparison",
        scale: .numeric([
            4: "Response is significantly clearer, more accurate, and more engaging than the baseline.",
            3: "Response is noticeably better than the baseline in most areas.",
            2: "Baseline is noticeably better than the response in most areas.",
            1: "Baseline is significantly clearer, more accurate, and more engaging than the response.",
        ]),
        judge: SystemLanguageModel.default
    )
}
```
> Unlike pointwise evaluation, the pairwise method uses its own built-in prompt and **automatically sends the sample's `expected` value to the model as judge as the baseline.**
> A score of 4 means the response is much better than the baseline, and a score of 1 means the baseline is much better. **The 1–4 scale has no neutral midpoint, so the judge has to decide which side of the comparison wins on every sample.**
> **A mean score above 2.5 indicates the model's responses are generally better than the baselines. A mean score below 2.5 indicates regressions. Scores near 2.5 suggest comparable quality.**

### 19.12 Judge design rules (from `designing-effective-model-judges`)

Scale-choice table, verbatim:
| Scale | Best for | Reliability |
|---|---|---|
| Binary, for example pass or fail | Safety, compliance, format checks, factual correctness | Highest |
| 1–4, or another even-numbered range | General quality, subjective dimensions like tone, clarity, helpfulness | Good |
| Custom categories | Domain-specific distinctions, for example, safe, borderline, or unsafe | Varies by design |

> **Start with binary scales for binary judgments.** ... Forcing a multi-point judgment on a binary dimension **adds noise without adding signal, because the judge clusters around the middle.**
> **Use a small, even number of levels for subjective quality.** ... an even number **removes the noncommittal middle** the model as judge can otherwise default to.
> Each level needs to describe **observable features** rather than restating a quality gradient. "Tags accurately represent the book and are useful for browsing" gives the model as judge something concrete to check. **"Excellent quality" does not.**

Good instructions = three parts, verbatim:
> - A **role** that frames the judge's expertise
> - **Criteria** that list the specific dimensions to assess
> - **Evaluation steps** that give the judge a procedure to follow before assigning a score
> Including steps promotes consistent evaluation by **preventing the model as judge from jumping to a score based on a first impression.**

Few-shot calibration, verbatim:
> Include examples that span the full range of your scale. At minimum, show what a high score and a low score look like. **Ideally, include an example at every level.**
> **TIP** — Add a final instruction such as "Use these examples to calibrate your scoring." to remind the model as judge to use the examples as reference points.

Combining judge + code evaluators:
```swift
private let nonEmpty = Metric("NonEmpty")
private let quality = Metric("Quality")

var evaluators: Evaluators {
    Evaluator { input, subject in
        return subject.value.isEmpty ? nonEmpty.failing() : nonEmpty.passing()
    }
    ModelJudgeEvaluator(
        "Quality",
        scale: .numeric([...]),
        judge: SystemLanguageModel.default,
        prompt: ModelJudgePrompt(instructions: """...""")
    )
}

func aggregateMetrics(using aggregator: inout MetricsAggregator) {
    aggregator.group("Validation") { group in
        group.computeMean(of: nonEmpty)
    }
    aggregator.group("Judge") { group in
        group.computeMean(of: quality)
    }
}
```
> When the model as judge scores a response, **it also produces a written rationale explaining its reasoning. These rationales appear in the detailed results alongside the score for each sample.** When scores seem wrong or inconsistent, the rationales usually show you why.

### 19.13 Synthetic datasets
```swift
actor SampleGenerator<SampleType> where SampleType : ModelSampleProtocol
init(_:samples:targetCount:sessionProvider:samplingStrategy:validator:)   // two overloads
var samplingStrategy: SampleGenerator.SamplingStrategy
var validator                             // "An optional closure that decides whether a generated sample is valid."
func run() -> AsyncStream                 // "Runs the generator and returns a stream of newly synthesized samples."
var samples                               // "All samples — initial and generated — from the most recent run."
var invalidSamples                        // "Samples that the validator rejected during the most recent run."
enum SampleGenerator.SamplingStrategy      // "how the generator selects existing samples as examples in the generation prompt"
```
> The framework adds a **`makeSamples(_:targetCount:sessionProvider:validator:)`** method to any array of `ModelSample` values. Call this method with a prompt that describes what to generate, and it returns new samples as an **asynchronous stream**.

Initial-dataset shape (verbatim):
```swift
// The categories the model can assign to extracted tasks.
// The @Generable macro lets the model produce instances of this type.
@Generable
enum TaskCategory: String, Codable, Sendable {
    case work
    case personal
    case health
    case errands
    case home
}

// The structured output the model produces for each input.
@Generable
struct TaskItem: Codable, Sendable {
    var title: String
    var dueOn: String?
    var category: TaskCategory
    var isUrgent: Bool
}

let dataset: [ModelSample<TaskItem>] = [
    // Here's a health task that is non-urgent and has a due date.
    ModelSample(
        prompt: "Schedule dentist appointment for next Tuesday",
        expected: TaskItem(title: "Schedule dentist appointment",
                           dueOn: "04/07/2026", category: .health, isUrgent: false)
    ),
    // ...
]
```
> For evaluations that score output without a reference answer, such as model-as-judge assessments of tone or fluency, **omit the expected value and generate prompt-only samples.**

### 19.14 Evaluation strategy (from `designing-effective-evaluations` + `designing-evaluation-criteria`)

Vague → precise table, verbatim:
| Vague goal | Precise criterion |
|---|---|
| "Stay within budget." | 100% compliance with stated budget ceiling (pass/fail) |
| "Be helpful." | Greater than 90% task success rate on common query benchmark |
| "Match the user's skill level." | Complexity score (1–4) within 0.5 of stated preference |
| "Generate accurate tags." | 95% of tags classify as factual descriptors, not sub… *(truncated in harvest)* |

> In Evaluations, the `Evaluation` protocol captures these three attributes directly: it bundles **the feature under test, the test dataset, the evaluators, and the result aggregation into a single, runnable definition.**
> **Treat evaluations as your living specification.**

Simple code-based evaluator:
```swift
Evaluator { input, subject in
    subject.value.split(separator: " ").count <= 200
        ? wordLimit.passing() : wordLimit.failing()
}
```

Dataset design article topics (not fully harvested): **golden sets, user profiles, challenge cases**.

Prompt-evaluation article (`/documentation/foundationmodels/evaluating-prompts-to-measure-performance-and-improve-model-responses`) key quotes:
> The response you get from a model **can vary even though you provide the same exact input.** This variation comes from the probabilistic nature of how the model generates text, and **from updates to the underlying model that you don't control.**
> Handle subjectiveness by translating your requirements into objective and measurable criteria. For example, you might determine that a recipe for a beginner involves **three to six ingredients and takes less than 20 minutes** to make.
> **Adding a single word to your prompt can dramatically change the model's behavior.** A change that improves one type of input might break others.
> This article applies to your evaluation strategy whether you choose to use **Swift or Python**. For more information about the Python Foundation Models SDK, see `https://github.com/apple/python-apple-fm-sdk`.

---

## 20. SPEECH FRAMEWORK

Index: `/documentation/speech` (60 KB). Two API generations coexist: the modern **SpeechAnalyzer** stack (iOS 26+) and the legacy **SFSpeechRecognizer** stack (iOS 10/17 era).

Top-level symbol inventory (from index link extraction):
**Modern:** `SpeechAnalyzer`, `SpeechModule`, `LocaleDependentSpeechModule`, `SpeechModuleResult`, `SpeechTranscriber`, `DictationTranscriber`, `SpeechDetector`, `AnalyzerInput`, `AnalyzerInputConverter`, `AnalysisContext`, `AssetInventory`, `AssetInstallationRequest`, `AssetInputSequenceProvider`, `CaptureInputSequenceProvider`, `SpeechModels`.
**Legacy:** `SFSpeechRecognizer`, `SFSpeechRecognizerDelegate`, `SFSpeechRecognitionRequest`, `SFSpeechAudioBufferRecognitionRequest`, `SFSpeechURLRecognitionRequest`, `SFSpeechRecognitionTask`, `SFSpeechRecognitionTaskDelegate`, `SFSpeechRecognitionTaskHint`, `SFSpeechRecognitionTaskState`, `SFSpeechRecognitionResult`, `SFSpeechRecognitionMetadata`, `SFTranscription`, `SFTranscriptionSegment`, `SFVoiceAnalytics`, `SFAcousticFeature`, `SFSpeechError`, `SFSpeechErrorDomain`, `SFSpeechRecognizerAuthorizationStatus`.
**Custom vocabulary (iOS 17 era, still current):** `SFCustomLanguageModelData`, `SFSpeechLanguageModel`, `DataInsertable`, `TemplateInsertable`.
**Articles/samples:** `asking-permission-to-use-speech-recognition`, `recognizing-speech-in-live-audio`, `bringing-advanced-speech-to-text-capabilities-to-your-app` (Sample Code, `iOS 26.0+, iPadOS 26.0+, Mac Catalyst 26.0+, macOS 26.0+, Xcode 26.0+`), `speech-recognition-in-objc`.

### 20.1 `SpeechAnalyzer`
```swift
final actor SpeechAnalyzer          // iOS 26.0+ … tvOS 26.0+, visionOS 26.0+
// Conforms: Actor, Sendable, SendableMetatype
```
> The `SpeechAnalyzer` class is responsible for: Holding associated modules; Accepting audio speech input; Controlling the overall analysis.
> Each module is responsible for: Providing guidance on acceptable input; Providing its analysis or transcription output.
> Analysis is asynchronous. Input, output, and session control are decoupled... **where an Objective-C API might use a delegate to provide results to you, the Swift API's modules provides their results via an `AsyncSequence`.**
> **The analyzer can only analyze one input sequence at a time.**

**Eight-step canonical flow, verbatim:**
> 1. Create and configure the necessary modules.
> 2. Ensure the relevant assets are installed or already present. See `AssetInventory`.
> 3. Create an input sequence you can use to provide the spoken audio. See helper classes `AssetInputSequenceProvider` and `CaptureInputSequenceProvider`.
> 4. Create and configure the analyzer with the modules and input sequence.
> 5. Supply audio. See helper class `AnalyzerInputConverter`.
> 6. Start analysis.
> 7. Act on results.
> 8. Finish analysis when desired.

**Full canonical example (verbatim — this is THE Speech "hello world" for 2026):**
```swift
import Speech

// Step 1: Modules
guard let locale = SpeechTranscriber.supportedLocale(equivalentTo: Locale.current) else {
    /* Note unsupported language */
}
let transcriber = SpeechTranscriber(locale: locale, preset: .transcription)

// Step 2: Assets
if let installationRequest = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
    try await installationRequest.downloadAndInstall()
}

// Step 3: Input sequence
let (inputSequence, inputBuilder) = AsyncStream.makeStream(of: AnalyzerInput.self)

// Step 4: Analyzer
let audioFormat = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [transcriber])
let analyzer = SpeechAnalyzer(modules: [transcriber])

// Step 5: Supply audio
let converter = AnalyzerInputConverter(analyzerFormat: audioFormat)
Task {
    while /* audio remains */ {
        let buffer = /* Get some audio */
        let inputs = try converter.convert(buffer, at: nil)
        for input in inputs {
            inputBuilder.yield(input)
        }
    }
    let inputs = try converter.flush()
    for input in inputs {
        inputBuilder.yield(input)
    }
    inputBuilder.finish()
}

// Step 7: Act on results
Task {
    do {
        for try await result in transcriber.results {
            let bestTranscription = result.text // an AttributedString
            let plainTextBestTranscription = String(bestTranscription.characters) // a String
            print(plainTextBestTranscription)
        }
    } catch {
        /* Handle error */
    }
}

// Step 6: Perform analysis
let lastSampleTime = try await analyzer.analyzeSequence(inputSequence)

// Step 8: Finish analysis
if let lastSampleTime {
    try await analyzer.finalizeAndFinish(through: lastSampleTime)
} else {
    try analyzer.cancelAndFinishNow()
}
```
> Note `converter.convert(buffer, at: nil)` returns **an array** of `AnalyzerInput`, and `flush()` returns a final array. Both are `throws` and **synchronous** (no `await`).

**Complete API surface:**
```swift
// Creating
init(modules:options:)
init(inputSequence:modules:options:analysisContext:volatileRangeChangedHandler:)
init(inputAudioFile:modules:options:analysisContext:finishAfterFile:volatileRangeChangedHandler:)

// Modules
func setModules(_:) async throws
var modules

// Performing analysis (structured concurrency)
final func analyzeSequence<InputSequence>(_ inputSequence: InputSequence) async throws -> CMTime?
    where InputSequence : Sendable, InputSequence : AsyncSequence, InputSequence.Element == AnalyzerInput
func analyzeSequence(from:) async throws -> CMTime?

// Autonomous analysis
func start(inputSequence:)
func start(inputAudioFile:finishAfterFile:)

// Finalizing / cancelling
func cancelAnalysis(before:)              // "Stops analyzing audio predating the given time."
func finalize(through:)                   // "Finalizes the modules' analyses."

// Finishing
func cancelAndFinishNow()
func finalizeAndFinishThroughEndOfInput()
func finalizeAndFinish(through:)
func finish(after:)

// Formats
static func bestAvailableAudioFormat(compatibleWith modules: [any SpeechModule]) async -> AVAudioFormat?
static func bestAvailableAudioFormat(compatibleWith:considering:) async -> AVAudioFormat?

// Responsiveness
func prepareToAnalyze(in:)
func prepareToAnalyze(in:withProgressReadyHandler:)

// Monitoring
func setVolatileRangeChangedHandler(_:)
var volatileRange                         // "The range of results that can change."

// Context
func setContext(_:)
var context
```

`analyzeSequence(_:)` return-value semantics, verbatim:
> The time-code of the last audio sample that was consumed from this or an earlier input sequence, or `nil` if no audio sample has been consumed. You may use this value for the parameter of `finalizeAndFinish(through:)`.
> When this method returns, **the last audio consumed from the input sequence may still be undergoing analysis.** To wait for the analysis to complete, call another method such as `finalize(through:)` and await its return.
> If you cancel the task executing this method, most input sequences will terminate early, causing this method to return early. **The method returns the time-code of the last audio sample that was consumed and does not throw `CancellationError`.**

`bestAvailableAudioFormat(compatibleWith:)`, verbatim:
> Returns `nil` if the specified modules require you to install additional assets.
> In order to keep `CMTime` values **sample-accurate**, the analyzer **does not transparently upsample, downsample, or convert audio input.**

**Finish-state semantics, verbatim:**
> When the analysis session transitions to the *finished* state:
> - The analyzer won't consume additional input from the input sequence (but note that **it doesn't drain or terminate the sequence**)
> - Most methods won't do anything; in particular, the analyzer won't accept different input sequences or modules
> - Module result streams terminate and modules won't publish additional results, though the app can continue to iterate over already-published results
>
> **NOTE** — While you can terminate the input sequence you created with a method such as `AsyncStream.Continuation.finish()`, **terminating the input sequence does *not* generally finish the analysis session**, and you can continue the session with a different input sequence. (See `finalizeAndFinishThroughEndOfInput()` for an exception.)

**Error semantics, verbatim:**
> When the analyzer or its modules' result streams throw an error, **the analysis session becomes finished** as described above, and the same error (or a `CancellationError`) is thrown from all waiting methods and result streams.

**Skipping audio, verbatim:**
> To skip past part of an audio stream, omit the buffers you want to skip from the input sequence. You can resume with a later buffer. When you resume analysis with a later `AVAudioPCMBuffer` buffer, you may need to supply the correct time-code to account for skipped audio. To do this, pass the time-code of the later buffer as the `bufferStartTime` parameter of the corresponding `AnalyzerInput` object.

### 20.2 `SpeechAnalyzer.Options` and simultaneity limits
```swift
struct Options                            // Equatable, Sendable
init(priority:modelRetention:)
init(priority:modelRetention:ignoresResourceLimits:)
var priority                              // "The priority of analysis processing work."
var modelRetention: Options.ModelRetention
var ignoresResourceLimits: Bool

enum ModelRetention                       // CaseIterable, Equatable, Hashable, Sendable
case lingering        // "Keeps the models in memory for a time so that they can be reused by another compatible analyzer session."
case processLifetime  // "Keeps the models in memory until this process exits."
case whileInUse       // "Releases the models when the analyzer is deallocated."
```
**Simultaneous-analysis limits — MAJOR FOOTGUN, verbatim:**
> The system normally limits simultaneous analyses to a conservative number, considering hardware capabilities of different devices. If you exceed that number, the system throws an **`insufficientResources`** error (`SFSpeechError.Code.insufficientResources`).
> To override the normal limits, create an analyzer with a `SpeechAnalyzer.Options` object with its `ignoresResourceLimits` value set to `true`. **The system allows an unlimited number of analyzers configured with this option. However, the hardware requirements of numerous analyzers will eventually exceed the system's actual capacity, and one or more of the analyzers will fail, throwing an unpredictable error.**
> **WARNING** — When using this option, test your app on a variety of devices under a variety of scenarios to experimentally determine how many analyzers you can reliably create and expect to function. Consider how to recover in the event one or more analyzers fail.

Lazy loading, verbatim:
> By default, the analyzer and modules **load the system resources that they require lazily**, and unload those resources when they're deallocated. To proactively load system resources and "preheat" the analyzer, call `prepareToAnalyze(in:)` after setting its modules.

### 20.3 `SpeechModule` / `SpeechModuleResult` / `LocaleDependentSpeechModule`
```swift
protocol SpeechModule : AnyObject, Sendable
var availableCompatibleAudioFormats       // "The audio formats that this module is able to analyze, given its configuration."
var results: Self.Results                 // AsyncSequence
associatedtype Result
associatedtype Results

protocol LocaleDependentSpeechModule : SpeechModule
protocol SpeechModuleResult
var range                                 // "The audio input range that this result applies to."
var isFinal: Bool                         // "Whether this result is final at the time it is produced."
var resultsFinalizationTime               // "The audio input time up to which results from this module have been finalized (after this result). The module's results are final up to but not including this time."
```
Conforming modules: `DictationTranscriber`, `SpeechDetector`, `SpeechTranscriber`.

### 20.4 `SpeechTranscriber`
```swift
final class SpeechTranscriber             // iOS 26.0+ … tvOS 26.0+, visionOS 26.0+
// Conforms: LocaleDependentSpeechModule, SpeechModule, Sendable

init(locale:preset:)
init(locale:transcriptionOptions:reportingOptions:attributeOptions:)

static var isAvailable: Bool              // "whether this module is available given the device's hardware and capabilities"
static var installedLocales
static var supportedLocales               // "including locales that may not be installed but are downloadable"
static func supportedLocale(equivalentTo:) -> Locale?

var results                               // AsyncSequence of SpeechTranscriber.Result
```
> Several transcriber instances **can share the same backing engine instances and models**, so long as the transcribers are configured similarly in certain respects.
> Use the `isAvailable` or `supportedLocales` properties to see if the current device supports the speech-to-text models used by `SpeechTranscriber`. **If it does not, consider disabling the feature or using `DictationTranscriber` instead.**

#### `SpeechTranscriber.Preset` — full matrix (verbatim table)
| Preset | `.volatileResults` | `.fastResults` | `.alternativeTranscriptions` | `.audioTimeRange` |
|---|---|---|---|---|
| `transcription` | No | No | No | No |
| `transcriptionWithAlternatives` | No | No | **Yes** | No |
| `timeIndexedTranscriptionWithAlternatives` | No | No | **Yes** | **Yes** |
| `progressiveTranscription` | **Yes** | **Yes** | No | No |
| `timeIndexedProgressiveTranscription` | **Yes** | **Yes** | No | **Yes** |

Descriptions, verbatim:
- `transcription` — "Configuration for basic, accurate transcription."
- `transcriptionWithAlternatives` — "Configuration for transcription with editing suggestions."
- `timeIndexedTranscriptionWithAlternatives` — "Configuration for transcription with editing suggestions, cross-referenced to source audio."
- `progressiveTranscription` — "Configuration for immediate transcription of live audio."
- `timeIndexedProgressiveTranscription` — "Configuration for immediate transcription of live audio, cross-referenced to stream time-codes."

```swift
struct Preset                             // Equatable, Hashable, Sendable
init(transcriptionOptions:reportingOptions:attributeOptions:)
var attributeOptions, reportingOptions, transcriptionOptions
```
> You can also create your own presets by extending this type.
```swift
let preset = SpeechTranscriber.Preset.timeIndexedTranscriptionWithAlternatives
let transcriber = SpeechTranscriber(
    locale: Locale.current,
    transcriptionOptions: preset.transcriptionOptions.union([.etiquetteReplacements])
    reportingOptions: preset.reportingOptions.subtracting([.alternativeTranscriptions])
    attributeOptions: preset.attributeOptions
)
```
> (Apple's snippet is **missing commas** between arguments — reproduced as-is. Options are `Set`-like: `.union`/`.subtracting`.)

#### Option enums (all `enum`, `CaseIterable, Equatable, Hashable, Sendable`)
```swift
enum SpeechTranscriber.TranscriptionOption
case etiquetteReplacements    // "Replaces certain words and phrases with a redacted form."

enum SpeechTranscriber.ReportingOption
case alternativeTranscriptions  // "Includes alternative transcriptions in addition to the most likely transcription."
case fastResults                // "Biases the transcriber towards responsiveness, yielding faster but also less accurate results."
case volatileResults            // "Provides tentative results for an audio range in addition to the finalized result."

enum SpeechTranscriber.ResultAttributeOption
case audioTimeRange             // "Includes time-code attributes in a transcription's attributed string."
case transcriptionConfidence    // "Includes confidence attributes in a transcription's attributed string."
```
> Note `transcriptionConfidence` is **not** in the preset matrix table — no preset enables it; you must use the designated initializer.

#### `SpeechTranscriber.Result`
```swift
struct Result                             // CustomStringConvertible, Equatable, Hashable, Sendable, SpeechModuleResult
var text: AttributedString                // "The most likely interpretation of the audio in this range."
var alternatives                          // "All the alternative interpretations of the audio in this range. The interpretations are in descending order of likelihood."
// inherited from SpeechModuleResult: range, isFinal, resultsFinalizationTime
```
> If the transcriber is configured to send volatile results, **each phrase is sent one or more times as the interpretation gets better and better until it is finalized.**

**AttributedString attribute scopes (Foundation, cross-framework):**
- `AttributeScopes.SpeechAttributes.TimeRangeAttribute` — "The time range in the source audio corresponding to the associated transcription text."
- `AttributeScopes.SpeechAttributes.ConfidenceAttribute` — "A confidence level (**0–1**) of the associated transcription text."
- `AttributedString.rangeOfAudioTimeRangeAttributes(intersecting:)` — "Returns the range of the attributed string that is within the given time range."

### 20.5 `DictationTranscriber`
```swift
final class DictationTranscriber          // iOS 26.0+ … visionOS 26.0+ (NO tvOS)
init(locale:preset:)
init(locale:contentHints:transcriptionOptions:reportingOptions:attributeOptions:)
static var installedLocales, supportedLocales
static func supportedLocale(equivalentTo:)
var results
```
> This transcriber uses **the same speech-to-text machine learning models as system dictation features** do, or as `SFSpeechRecognizer` does when it is configured for on-device operation. **This transcriber does not support languages or locales that `SFSpeechRecognizer` only supports via network access.**

Three accuracy levers, verbatim:
> - To **bias recognition towards certain words**, create an `AnalysisContext` object and add those words to its `contextualStrings` property. Create a `SpeechAnalyzer` instance with that context object or set the analyzer's `context` property.
> - To **supply custom vocabulary**, create an `SFSpeechLanguageModel` object and configure the transcriber with a corresponding `customizedLanguage(modelConfiguration:)` option.
> - To **adjust the transcriber's algorithm**, configure the transcriber with relevant `DictationTranscriber.ContentHint` parameter. For example, you may use `farField` hint to improve accuracy of distant speech.

#### `DictationTranscriber.ContentHint`
```swift
struct ContentHint                        // Equatable, Hashable, Sendable
static var shortForm      // "A processing hint indicating that the audio is only expected to be a minute or so long."
static var farField       // "A processing hint indicating that the audio should be processed as if it were from a speaker far from the microphone."
static var atypicalSpeech // "A processing hint indicating that the audio is from a speaker with a heavy accent, lisp, or other confounding factor."
static func customizedLanguage(modelConfiguration:)  // "A hint specifying a custom language model applicable to the expected spoken audio content."
```
> These hints optimize transcription, but **do not preclude spoken audio with different characteristics.**

#### `DictationTranscriber.Preset` — full matrix (verbatim table)
| Preset | `shortForm` | `.volatileResults` | `.frequentFinalization` | `.audioTimeRange` | `.punctuation` |
|---|---|---|---|---|---|
| `phrase` | **Yes** | No | No | No | No |
| `shortDictation` | **Yes** | No | No | No | **Yes** |
| `progressiveShortDictation` | **Yes** | **Yes** | **Yes** | No | **Yes** |
| `longDictation` | No | No | No | No | **Yes** |
| `progressiveLongDictation` | No | **Yes** | No | No | **Yes** |
| `timeIndexedLongDictation` | No | No | No | **Yes** | **Yes** |

Descriptions, verbatim:
- `phrase` — "Configuration for a short phrase without punctuation."
- `shortDictation` — "Configuration for about a minute of audio."
- `progressiveShortDictation` — "Configuration for immediate transcription of about a minute of live audio."
- `longDictation` — "Configuration for more than a minute of audio."
- `progressiveLongDictation` — "Configuration for immediate transcription of lengthy audio."
- `timeIndexedLongDictation` — "Configure for lengthy audio, cross-referencing words to time-codes."

```swift
struct Preset
init(contentHints:transcriptionOptions:reportingOptions:attributeOptions:)
var attributeOptions, contentHints, reportingOptions, transcriptionOptions
```
```swift
let preset = DictationTranscriber.Preset.shortDictation
let transcriber = DictationTranscriber(
    locale: Locale.current,
    contentHints: preset.contentHints,
    transcriptionOptions: preset.transcriptionOptions.union([.emoji])
    reportingOptions: preset.reportingOptions
    attributeOptions: preset.attributeOptions
)
```
> Dictation-specific option cases seen only in these tables/snippets: `DictationTranscriber.TranscriptionOption.punctuation`, `.emoji`, `DictationTranscriber.ReportingOption.frequentFinalization`, `.volatileResults`, `DictationTranscriber.ResultAttributeOption.audioTimeRange`. **Full case lists for the DictationTranscriber option enums were NOT fetched** — see Open Questions.

### 20.6 `SpeechDetector` (VAD)
```swift
final class SpeechDetector                // iOS 26.0+ … tvOS 26.0+, visionOS 26.0+
init()                                    // "Creates a speech detector with default settings."
init(detectionOptions:reportResults:)
struct SpeechDetector.DetectionOptions
enum/struct SpeechDetector.SensitivityLevel   // has at least .medium
var results
struct SpeechDetector.Result
```
> This module asks "is there speech?" and provides you with the ability to **gate transcription by the presence of voices, saving power** otherwise used by attempting to transcribe what is likely to be silence.
```swift
let transcriber = SpeechTranscriber(..)
let speechDetector = SpeechDetector()
let analyzer = SpeechAnalyzer(.., modules: [speechDetector, transcriber])
```
```swift
let analyzer = SpeechAnalyzer(..)
let transcriber = SpeechTranscriber(..)
let speechDetector = SpeechDetector()
try await analyzer.setModules([transcriber, speechDetector])
```
> **IMPORTANT** — This module **only functions in conjunction with a `SpeechTranscriber` or `DictationTranscriber` module.**
> **NOTE** — For certain use cases, such as those with a lot of silence, it might be tempting to always enable voice activated transcription. But **if the model drops audio that does contain speech, there could be a tradeoff** between the power being saved by always having VAD enabled and potentially lower accuracy transcriptions. You can set the aggressiveness of the VAD model with `SpeechDetector.SensitivityLevel`. **While `.medium` is recommended for most use cases**, the value of these tradeoffs will be context-specific.
> `SpeechDetector.Result`: "Please note, these must be enabled via [`reportResults`] and currently only support **error handling from the VAD model**." — i.e. the Result stream is NOT a stream of speech/silence booleans.

### 20.7 Asset management (`AssetInventory`)
```swift
final class AssetInventory                // iOS 26.0+ … tvOS 26.0+, visionOS 26.0+
static func assetInstallationRequest(supporting modules: [any SpeechModule]) async throws -> AssetInstallationRequest?
static func reserve(locale:) async throws
static func release(reservedLocale:) async
static var reservedLocales
static var maximumReservedLocales: Int
static func status(forModules:) async -> AssetInventory.Status

enum AssetInventory.Status                // Comparable, Equatable, Hashable
case downloading   // "The system is currently downloading the assets, or waiting for conditions to improve and continue downloading later."
case installed     // "The necessary assets have been downloaded and installed on the device, and the module is ready for use."
case supported     // "The module can work with its configuration, but the assets will need to be downloaded."
case unsupported   // "The module will not work with its configuration."
```
> `Status` is **`Comparable`** — presumably ordered `unsupported < supported < downloading < installed`. **UNVERIFIED ordering.**

**Four-step install process, verbatim:**
> 1. Create analyzer modules in the configurations that you wish to use. **These modules can be discarded when no longer needed; the system installs assets using the modules' configuration, not their object identity.**
> 2. Assign your app's asset reservations to those locales. The class does this automatically if needed, but you can also call `reserve(locale:)` to do this manually. **This step is only necessary for modules with locale-specific assets**; that is, modules conforming to `LocaleDependentSpeechModule`.
> 3. Start downloading the required assets... Call `assetInstallationRequest(supporting:)` to obtain an instance of `AssetInstallationRequest` and call its `downloadAndInstall()` method.
> 4. Wait for the download to finish. Note that **the download may finish immediately**; the assets may have already been downloaded if the assets were preinstalled on the system, another app already downloaded them, or a previous module configuration used the same assets.

Key constraints, verbatim:
> These assets are **machine-learning models downloaded from Apple's servers and managed by the system**. Once you download, install, or use an asset, the system **retains and updates it automatically, and shares it with other apps**. The system makes a certain number of **locale-specific asset reservations** available to your app to limit storage space and network usage.
> **Your app does not work with assets directly.** Instead, your app configures module objects. The system uses the modules' configuration to determine what assets are relevant.
> Once assets are downloaded, they persist between app launches and are shared between apps. **The system may unsubscribe your app from assets that haven't been used in a while.**
> When your app no longer needs assets for a particular locale, call `release(reservedLocale:)` to free up that reservation. **The system will remove the assets at a later time.**

`assetInstallationRequest(supporting:)`, verbatim:
> If the current status is `.installed`, **returns nil**, indicating that nothing further needs to be done.
> If some of the assets require locales that aren't reserved, **it automatically reserves those locales. If that would exceed `maximumReservedLocales`, then it throws an error.**

```swift
@objc final class AssetInstallationRequest   // inherits NSObject, conforms ProgressReporting
func downloadAndInstall() async throws
```
> You do not create instances of this type directly. **The system consolidates download and installation requests; you may obtain several of these instances and call `downloadAndInstall()` several times without causing redundant downloads.**
> Conforms to **`ProgressReporting`** → has a `progress: Progress` for UI.

### 20.8 Input plumbing (mostly NEW in 2026)
```swift
struct AnalyzerInput                      // iOS 26.0+, Sendable — "Time-coded audio data."
init(buffer:)                             // two overloads (-3nt02, -2ysg3)
init(buffer:bufferStartTime:)             // "for audio that may be discontiguous with previous input"
var bufferStartTime                       // "The time-code of this input."
var bufferDuration                        // "The length of this input."
var bufferFormat                          // "The audio format of this input."
var buffer                                // *(Deprecated)* "A new copy of the audio data for this input."
```
> The audio data **must** have an audio format that is supported by the analyzer's modules; **the analyzer does not perform audio conversion.**
> The audio format **may differ from one `AnalyzerInput` object to the next.** If the new audio format is supported by the modules, the modules will be reconfigured as needed.

```swift
final class AnalyzerInputConverter        // NEW iOS 27.0+ Beta
static func converter(compatibleWith:) -> AnalyzerInputConverter
init(analyzerFormat:configurationHandler:)
func convert(_:at:) throws -> [AnalyzerInput]
func flush() throws -> [AnalyzerInput]
```
```swift
final class AssetInputSequenceProvider    // NEW iOS 27.0+ Beta
static func provider(from:compatibleWith:priority:)         // "reads from the first track of an asset or file"
static func provider(from:track:compatibleWith:priority:)
init(asset:track:analyzerFormat:priority:)
var analyzerInputs                        // AsyncSequence of AnalyzerInput
```
```swift
final class CaptureInputSequenceProvider  // NEW iOS 27.0+ Beta
static func providerWithSession(from:compatibleWith:priority:)  // "configures a NEW audio capture session with that device"
static func provider(from:in:compatibleWith:priority:)          // uses an existing session
init(session:analyzerFormat:priority:)
var analyzerInputs
var captureSession                        // "The underlying capture session."
var captureAudioDataOutput                // "An audio data output that routes and converts captured audio buffers to async sequences."
```
> Get the provider object's `analyzerInputs` property to convert the source's audio to a supported format and obtain an asynchronous input sequence... Pass that sequence to `analyzeSequence(_:)`, `start(inputSequence:)`, or a similar parameter of the analyzer's initializer.
> To end the analysis session after processing the audio track or captured audio, call one of the analyzer's `finish` methods. **Otherwise, by default, the analyzer won't terminate its result streams and will wait for additional audio input sequences or buffers.**

```swift
final class AnalysisContext               // iOS 26.0+
var contextualStrings                     // bias words
```
```swift
enum SpeechModels                         // iOS 26.0+ — asset/resource namespace
```

### 20.9 Custom vocabulary (legacy but current)
```swift
class SFCustomLanguageModelData           // iOS 17.0+, macOS 14.0+ — Codable, Equatable, Hashable
init(locale:identifier:version:builder:)  // result-builder form
init(locale:identifier:version:)          // empty container
@resultBuilder SFCustomLanguageModelData.DataInsertableBuilder
@resultBuilder SFCustomLanguageModelData.TemplateInsertableBuilder

func insert(term:)                        // "Add a custom term to the vocabulary."
static func supportedPhonemes(locale:)    // "List the supported subset of X-SAMPA pronunciations supported by this locale"
struct SFCustomLanguageModelData.CustomPronunciation

func insert(phraseCount:)                 // "Add a sample to the body of training data."
struct SFCustomLanguageModelData.PhraseCount  // "A phrase used to bias the language model, along with a weight influencing the relative strength of the bias."

struct SFCustomLanguageModelData.PhraseCountsFromTemplates
class SFCustomLanguageModelData.TemplatePhraseCountGenerator
class SFCustomLanguageModelData.PhraseCountGenerator      // "Abstract base class"
func insert(phraseCountGenerator:)

func export(to:) async throws             // "Export the accumulated data to a file."
var identifier, locale, version

protocol DataInsertable
protocol TemplateInsertable
class SFCustomLanguageModelData.CompoundTemplate          // "You are not intended to use this directly."
```
> Pronunciations use **X-SAMPA**, and the supported phoneme subset is **locale-specific** (`supportedPhonemes(locale:)`).

```swift
class SFSpeechLanguageModel               // iOS 17.0+, macOS 14.0+ (NO tvOS) — inherits NSObject
static func prepareCustomLanguageModel(for:configuration:completion:)
static func prepareCustomLanguageModel(for:configuration:ignoresCache:completion:)
static func prepareCustomLanguageModel(for:clientIdentifier:configuration:completion:)              // *(Deprecated)*
static func prepareCustomLanguageModel(for:clientIdentifier:configuration:ignoresCache:completion:) // *(Deprecated)*
struct/class SFSpeechLanguageModel.Configuration   // "An object describing the location of a custom language model and specialized vocabulary."
```
> The `clientIdentifier:` variants are deprecated — migrate to the two-arg forms.
> Wiring into the modern stack: `DictationTranscriber.ContentHint.customizedLanguage(modelConfiguration:)` takes an `SFSpeechLanguageModel.Configuration`.
> **`SpeechTranscriber` has no `ContentHint`** — custom language models are a `DictationTranscriber`-only feature.

---

## 21. Cross-framework links discovered

| Other framework | Symbol/path seen | Why it matters |
|---|---|---|
| **Vision** | `/documentation/Vision/OCRTool`, `/documentation/Vision/BarcodeReaderTool` | Built-in `Tool` conformances Apple ships for multimodal FM sessions. NOT harvested this session. |
| **TabularData** | `DataFrame` (in `EvaluationResult.summary` / `.detailed`) | Evaluation results are DataFrames; typed column subscripts. |
| **Swift Testing** | `TestTrait`, `TestScoping`, `Trait`, `@Test(.evaluates(_:))`, `#expect` | Evaluations runs entirely inside Swift Testing. |
| **Observation** | `LanguageModelSession : Observable`, `SystemLanguageModel : Observable`, `PrivateCloudComputeLanguageModel : Observable` | Direct SwiftUI binding of `transcript` / `isResponding` / `availability` / `quotaUsage`. |
| **Foundation** | `AttributeScopes.SpeechAttributes.TimeRangeAttribute`, `.ConfidenceAttribute`, `AttributedString.rangeOfAudioTimeRangeAttributes(intersecting:)` | Speech results are `AttributedString`. |
| **AVFAudio / AVFoundation** | `AVAudioFormat`, `AVAudioBuffer`, `AVAudioPCMBuffer`, `AVAsset` tracks, AV capture session | Speech input pipeline. |
| **CoreMedia** | `CMTime` (all SpeechAnalyzer time-codes) | Sample-accurate timing. |
| **CoreGraphics / CoreImage / CoreVideo** | `CGImage`, `CIImage`, `CVPixelBuffer` | FM image attachments. |
| **UniformTypeIdentifiers** | `UTType` | How FM infers a URL is an image. |
| **BundleResources** | `com.apple.developer.private-cloud-compute` | PCC managed entitlement. |
| **Instruments** | "Foundation Models" template | Token/latency profiling. |
| **GitHub (Apple)** | `apple/foundation-models-utilities`, `apple/coreai-models`, `apple/python-apple-fm-sdk`, `ml-explore/mlx-swift-lm` | The open-source surface. |

---

## 22. Consolidated gotchas / footguns

1. **`LanguageModelSession.GenerationError` is deprecated but binary-compatible.** "Apps built with Xcode 26 will continue to catch this error until you rebuild with Xcode 27. You must update to Xcode 27 to catch the new error types before submitting your app." Rebuilding with Xcode 27 **silently changes which `catch` clauses fire.**
2. **`Transcript.Entry` gained `.reasoning`; `Transcript.Segment` gained `.attachment`.** Exhaustive switches from iOS 26 fail to compile against the iOS 27 SDK.
3. **`toolCallingMode: .required` with no exit condition = infinite tool-call loop.** Must throw from `call(arguments:)` or flip the mode via a `DynamicProfile`.
4. **On-device context window is exactly 4096 tokens per session.** PCC is 32K. Everything counts: instructions, prompts, tool definitions + I/O, `Generable` JSON schemas, responses.
5. **`maximumResponseTokens` produces truncated/ungrammatical output** ("A cat is a small."). Prefer prompt-level length instructions and `@Guide(.maximumCount(_:))`.
6. **Sampling seeds are best-effort, not deterministic.** Stated twice.
7. **`permissiveContentTransformations` only affects string generation.** Guided generation still runs default guardrails.
8. **Apple can update guardrails outside the OS release cycle.** Prompts that pass today can start failing without an OS update.
9. **Prompt injection:** never put user input in `Instructions`. The model prioritizes instructions over prompts.
10. **KV cache invalidation:** changing instructions invalidates the entire downstream cache including all transcript entries. Conditional content must go **last** in a `DynamicInstructions` body.
11. **Removing a tool mid-session leaves dangling transcript references** and degrades accuracy. Adding a tool late is often ignored by the model.
12. **Stateful `historyTransform` / `onResponse` mutations invalidate cache every turn.** Prefer stateless, entry-count-preserving transforms.
13. **Session history is read-only inside `DynamicInstructions` and `Tool`** (writable only in profile life-cycle callbacks).
14. **`isResponding` must be checked** — concurrent `respond` calls throw `LanguageModelSession.Error.concurrentRequests`.
15. **Streaming in the background risks `LanguageModelError.rateLimited`** — use non-streaming `respond` instead.
16. **PCC needs a managed entitlement + eligibility approval.** Not self-serve.
17. **PCC quota is orthogonal to availability** — a model can be `.available` and still throw `quotaLimitReached`.
18. **PCC availability has `.systemNotReady`**, which `SystemLanguageModel.Availability.UnavailableReason` does not.
19. **Instruments traces store prompts and responses UNENCRYPTED.**
20. **Speech: `SpeechAnalyzer` analyzes one input sequence at a time**, and the system caps simultaneous analyzers; exceeding throws `insufficientResources`. `ignoresResourceLimits: true` removes the cap but leads to "an unpredictable error" at real hardware limits.
21. **Speech: terminating the input `AsyncStream` does NOT finish the analysis session.** You must call a `finish` method (or deallocate the analyzer), else result streams never terminate.
22. **Speech: the analyzer does no audio conversion** — you must feed `bestAvailableAudioFormat(...)`. It refuses to resample to keep `CMTime` sample-accurate.
23. **Speech: `bestAvailableAudioFormat` returns `nil` if assets aren't installed** — order matters (assets before format query).
24. **Speech: `assetInstallationRequest(supporting:)` returns `nil` when already installed** — do not force-unwrap.
25. **Speech: auto-reservation can throw** if it would exceed `maximumReservedLocales`.
26. **`DictationTranscriber` has no tvOS; `SpeechTranscriber` has no watchOS at all** (neither transcriber lists watchOS).
27. **`SpeechDetector` only works alongside a transcriber module**, and its `Result` stream is for VAD *errors*, not speech/silence events.
28. **`SpeechTranscriber` has no `ContentHint`** — custom language models (`SFSpeechLanguageModel`) only bind to `DictationTranscriber`.
29. **Evaluations `JSONLoader` silently skips malformed rows** (logged to `OSLog` only) — a corrupt dataset shrinks your eval without failing.
30. **Multilingual: every input is language-sensitive**, including `Generable` property names and `@Guide` text.
31. **Apple's own code samples in these docs contain errors** — the `GenerationID` SwiftUI sample has unbalanced braces and `for try! await`; both `Preset` snippets omit commas between arguments; `DynamicGenerationSchema.Property` array is missing a trailing comma. Don't copy-paste blindly.
32. **`@Generable` enums used for classification want `samplingMode: .greedy`**, otherwise the model "may select an option that's close."

---

## 23. Source inventory (every URL fetched this session)

All fetched as `https://sosumi.ai<path>` → mirrors `https://developer.apple.com<path>`. All returned **HTTP 200** unless noted.

**Framework indexes**
`/documentation/foundationmodels` (121 KB) · `/documentation/speech` (60 KB) · `/documentation/evaluations` (44 KB) · `/documentation/updates/foundationmodels` · `/documentation/updates/speech`

**FoundationModels — articles**
`/adding-intelligent-app-features-with-generative-models` · `/adding-server-side-intelligence-with-private-cloud-compute` · `/analyzing-images-with-multimodal-prompting` · `/analyzing-the-runtime-performance-of-your-foundation-models-app` · `/categorizing-and-organizing-data-with-content-tags` · `/composing-dynamic-sessions-with-instructions-and-profiles` · `/evaluating-prompts-to-measure-performance-and-improve-model-responses` · `/expanding-generation-with-tool-calling` · `/generating-content-and-performing-tasks-with-foundation-models` · `/generating-swift-data-structures-with-guided-generation` · `/improving-the-safety-of-generative-model-output` · `/managing-the-context-window` · `/optimizing-key-value-caching-in-language-model-sessions` · `/prompting-an-on-device-foundation-model` · `/supporting-languages-and-locales-with-foundation-models` · `/updating-prompts-for-new-model-versions`

**FoundationModels — symbols**
`/languagemodelsession` · `/languagemodelsession/respond(to:options:)` · `/respond(options:prompt:)` · `/respond(to:generating:includeschemainprompt:options:)` · `/respond(to:options:contextoptions:metadata:)` · `/streamresponse(to:generating:includeschemainprompt:options:)` · `/prewarm(promptprefix:)` · `/isresponding` · `/transcript` · `/init(model:tools:instructions:)` · `/init(model:tools:transcript:)` · `/init(model:dynamicinstructions:history:)` · `/init(profile:history:)` · `/usage-swift.struct` · `/response` · `/responsestream` · `/responsestream/snapshot` · `/error` · `/toolcallerror` · `/generationerror` · `/logfeedbackattachment(sentiment:issues:desiredoutput:)` · `/dynamicprofile` · `/dynamicprofilebuilder` · `/dynamicprofilemodifier` · `/profile` · `/sessionproperty`
`/systemlanguagemodel` + `/availability-swift.enum` · `/usecase` · `/guardrails` · `/guardrails/permissivecontenttransformations` · `/contextsize` · `/supportedlanguages` · `/supportslocale(_:)` · `/tokencount(for:)` · `/init(usecase:guardrails:)` · `/error`
`/generationoptions` + `/samplingmode-swift.struct` · `/samplingmode-swift.struct/random(top:seed:)` · `/samplingmode-swift.struct/random(probabilitythreshold:seed:)` · `/toolcallingmode-swift.struct` · `/temperature` · `/maximumresponsetokens` · `/init(samplingmode:temperature:maximumresponsetokens:toolcallingmode:)`
`/transcript` + `/entry` · `/segment` · `/reasoning` · `/imageattachment` · `/prompt` · `/structuredsegment` · `/attachmentsegment` · `/history` · `/structuredtranscript`
`/generable` · `/generationschema` · `/dynamicgenerationschema` · `/generatedcontent` · `/generationguide` · `/generationid` · `/instructions` · `/prompt` · `/tool` · `/tool/call(arguments:)` · `/contextoptions` · `/contextoptions/reasoninglevel-swift.enum` · `/transcripterrorhandlingpolicy` · `/languagemodelerror` · `/languagemodelerror/guardrailviolation` · `/languagemodel` · `/languagemodelcapabilities` · `/languagemodelcapabilities/capability` · `/languagemodelexecutor` · `/languagemodelexecutorgenerationchannel` · `/languagemodelexecutorgenerationrequest` · `/languagemodelfeedback` · `/languagemodelfeedback/issue` · `/languagemodelfeedback/sentiment` · `/privatecloudcomputelanguagemodel` · `/privatecloudcomputelanguagemodel/error` · `/privatecloudcomputelanguagemodel/quotausage-swift.struct` · `/attachment` · `/imageattachmentcontent` · `/imagereference` · `/dynamicinstructions` · `/dynamicinstructionsbuilder` · `/dynamicinstructionsforeach` · `/sessionpropertykey` · `/sessionpropertyvalues`

**Evaluations**
`/evaluating-language-model-responses` · `/designing-effective-evaluations` · `/designing-effective-model-judges` · `/designing-evaluation-criteria` · `/designing-evaluation-datasets` · `/evaluating-tool-calling-behavior` · `/generating-synthetic-evaluation-datasets` · `/scoring-with-model-as-judge-evaluators` · `/book-tracker-using-evaluations-to-evaluate-an-intelligent-feature` (31 KB, fetched but only skimmed) · `/evaluation` · `/evaluator` · `/evaluatorprotocol` · `/metric` · `/metricsaggregator` · `/modeljudgeevaluator` · `/modeljudgeprompt` · `/modelsample` · `/toolcallevaluator` · `/toolexpectation` · `/trajectoryexpectation` · `/argumentmatcher` · `/arrayloader` · `/jsonloader` · `/samplegenerator` · `/scoredimension` · `/scoringscale` · `/evaluationtrait` · `/evaluationresult`

**Speech**
`/speechanalyzer` · `/speechanalyzer/options` · `/speechanalyzer/options/modelretention-swift.enum` · `/speechanalyzer/analyzesequence(_:)` · `/speechanalyzer/bestavailableaudioformat(compatiblewith:)` · `/speechtranscriber` · `/speechtranscriber/preset` · `/transcriptionoption` · `/reportingoption` · `/resultattributeoption` · `/result` · `/dictationtranscriber` · `/dictationtranscriber/preset` · `/dictationtranscriber/contenthint` · `/speechdetector` · `/speechmodule` · `/speechmoduleresult` · `/speechmodels` · `/localedependentspeechmodule` · `/analyzerinput` · `/analyzerinputconverter` · `/analysiscontext` · `/assetinventory` · `/assetinventory/status` · `/assetinventory/assetinstallationrequest(supporting:)` · `/assetinstallationrequest` · `/assetinputsequenceprovider` · `/captureinputsequenceprovider` · `/sfcustomlanguagemodeldata` · `/sfspeechlanguagemodel` · `/datainsertable` · `/templateinsertable` · `/bringing-advanced-speech-to-text-capabilities-to-your-app`

**404s encountered:** only from my own URL-encoding bug (paren-stripped paths). After correcting, **zero genuine 404s**. `/documentation/evaluations` — which the task flagged as possibly 404 — **exists and is substantial.**

Local mirror of all raw markdown: `/private/tmp/claude-501/-Volumes-ExtStor-FM-and-MLX-and-CoreAI/064ca93f-3a95-445f-9fa4-7cd79f77f3b0/scratchpad/sos/` (session-scoped; will not persist).

---

## 24. Open questions / UNVERIFIED

1. **`init(model:tools:instructions:)` generic-ness.** The declaration page says `model: SystemLanguageModel = .default`, but the PCC article says you can pass `PrivateCloudComputeLanguageModel` to it. Either an unlisted iOS 27 overload exists or the article is wrong.
2. **`@Guide` variadic-only form.** `@Guide(.minimumCount(1), .maximumCount(20))` (no `description:`) is used in Apple's own sample but matches neither documented macro signature.
3. **`GenerationGuide.count(_:)` overloads.** Used with both `4` and `3...8`.
4. **Life-cycle closure arities.** `onToolCall` appears with 0 and 1 params; `onResponse` with 0 and 1. Exact signatures not documented on any fetched page.
5. **`ScoringMode` cases.** Referenced as a `ModelJudgeEvaluator` parameter; page not fetched.
6. **`PrivateCloudComputeLanguageModel.QuotaUsage.Status` case list.** Only `.belowLimit(let info)` (with `info.isApproachingLimit`) observed.
7. **`PrivateCloudComputeLanguageModel.Availability.UnavailableReason` full case list.** Only `.deviceNotEligible` and `.systemNotReady` observed.
8. **`LanguageModelFeedback.Issue.Category` case list.** Only `.incorrect` observed.
9. **`GenerationError.decodingFailure` successor** in the new error taxonomy.
10. **`DictationTranscriber.TranscriptionOption` / `.ReportingOption` / `.ResultAttributeOption` full case lists.** Only `punctuation`, `emoji`, `volatileResults`, `frequentFinalization`, `audioTimeRange` inferred from preset tables and snippets. Pages not fetched.
11. **`SpeechDetector.DetectionOptions` and `.SensitivityLevel` full member lists.** Only `.medium` observed.
12. **`AssetInventory.Status` `Comparable` ordering.**
13. **`ImageReference.resolved(in:)` parameter type** — `ArraySlice<Transcript.Entry>` (new) vs `Transcript` (deprecated `resolve(in:)`).
14. **`ArgumentMatcher.exact` value type** — bare `String` vs `.string(_:)` case.
15. **`EvaluatorsBuilder` has `buildOptional` but no `buildEither`** — `if/else` in `evaluators` blocks may not compile.
16. **`Origami: Crafting a dynamic tutorial for Apple Intelligence`** sample-code page NOT fetched — likely the richest dynamic-profiles example available.
17. **`Generate dynamic game content with guided generation and tools`** sample NOT fetched.
18. **`Book Tracker`** (31 KB) fetched but only skimmed — contains a full CLI synthetic-data generator + combined code/judge/tool evaluation. Deserves its own pass.
19. **Vision `OCRTool` / `BarcodeReaderTool` declarations** — not harvested.
20. **`com.apple.developer.private-cloud-compute` entitlement page** — not harvested (value type, provisioning requirements).
21. **`#Playground` macro** — referenced in the Feb 2026 release notes but its documentation page was not located.
22. **Whether `ContextOptions.reasoningLevel` is a no-op on `SystemLanguageModel`.** The PCC table says on-device reasoning is "Not supported", but `ContextOptions` is not gated to PCC in the type system.
23. **`SessionPropertyEntry()` macro declaration** — used as `@SessionPropertyEntry` (no parens) in all samples but named with parens in the index.
24. **Python SDK (`apple/python-apple-fm-sdk`) surface** — referenced twice in Apple docs; no Apple-hosted documentation page found.
