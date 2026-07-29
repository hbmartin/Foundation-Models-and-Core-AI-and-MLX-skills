# apple/foundation-models-utilities — deep dive

> **Provenance.** Every claim below is grounded in a file read during this session from the local
> clone at `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__foundation-models-utilities`
> at commit `376ca60` (tag `1.0.0-beta3`, 2026-07-10). Citations use `path/file.swift:LINE`.
> Anything not verifiable from a file in this repo is explicitly marked **UNVERIFIED**.
> Nothing here is written from model memory.

---

## 1. Repository facts

| Fact | Value | Source |
|---|---|---|
| Full name | `apple/foundation-models-utilities` | `gh repo view` |
| Description | "Emerging and experimental patterns for building with the Foundation Models framework" | `gh repo view` |
| Created | 2026-06-08T04:40:53Z | `gh repo view` |
| Last push | 2026-07-16T13:23:54Z | `gh repo view` |
| Stars / forks | 459 / 24 | `gh repo view` |
| License | Apache License 2.0 | `LICENSE.txt`, `gh repo view` |
| Archived | no | `gh repo view` |
| **Issues** | **DISABLED on GitHub** | `gh issue list` → `"the 'apple/foundation-models-utilities' repository has disabled issues"` |
| **Pull requests** | **zero, all states** | `gh pr list -R … --state all --limit 50` returned empty |
| GitHub releases | **none** (`gh release list` empty) | — |
| Git tags | `1.0.0-beta1` → `a047a50`; `1.0.0-beta3` → `376ca60` | `git ls-remote --tags` |
| Branches | `main` only | `git branch -a` |
| Total commits | **2** | `git log --oneline -50` |

### Commit history in full (only two commits exist)

```
376ca60  Updates to accompany Xcode 27 beta 3     Erik Hornberger <erik_h@apple.com>  Fri Jul 10 17:10:52 2026 -0400
a047a50  Hello foundation-models-utilities        Erik Hornberger <erik_h@apple.com>  Sun Jun 7 21:50:02 2026 -0700
```

Co-authors on the initial commit (all `@apple.com`): `oliveroneill`, `mkery`, `erik-apple`,
`matthewfernst`, `rxwei`, `li3zhen1`, `louisdh`, `egourlao`. Note **`rxwei`** — Richard Wei, of
Swift-for-TensorFlow / Swift compiler fame.

Commit `376ca60`'s message is itself a release-note-grade changelog and is the single best summary
of what changed between Xcode 27 beta 1 and beta 3 in the *framework* API surface:

```
  - Renamed SamplingMode enum cases — `.top` → `.randomTopK` and `.nucleus` → `.randomProbabilityThreshold`.
  - Removed `.model(any LanguageModel)` modifier since it's now included in the Foundation Models framework.
  - `SkillActivations` no longer conforms to `RandomAccessCollection` — replaced with a public
    `activeSkillNames` property and an `isActive(_:)` method.
  - Added `urlSessionConfiguration` parameter to `ChatCompletionsLanguageModel.init` — allows tuning
    timeouts, proxies, and other transport settings; defaults to an ephemeral configuration.
  - Added instructions parameter to `Skills` — lets callers override the default leading instructions
    rendered above the skill list.
  - `Skills` now emits a default leading instruction telling the model to silently activate a matching
    skill or otherwise respond normally.
  - `ToggleSkillTool` default description — now instructs the model to activate without asking permission
    or announcing activation.
  - Improved skill instructions formatting — skills are now separated by blank lines rather than inline
    `\n\n` strings; skill headers and descriptions are emitted as separate `Instructions` lines.
  - `ChatCompletionsLanguageModel` schema name uses the new `GenerationSchema.name` API.
  - Fixed `SkillActivations` observation.
```

### Issue reporting policy

`README.md:12` and `CONTRIBUTING.md` both route issues away from GitHub:

- `README.md:12` — "💬 **Issue reporting**: [Apple Developer Forums](https://developer.apple.com/forums/topics/machine-learning-and-ai/machine-learning-and-ai-foundation-models)"
- `CONTRIBUTING.md` — "We're just getting started here. Stay tuned! **This project is not currently accepting PRs.**"
  and directs bugs to the Developer Forums or Feedback Assistant.

`CONTRIBUTING.md` also gives a notable repro-request checklist that names an otherwise-undocumented
API: **`session.logFeedbackAttachment`** — "Run `session.logFeedbackAttachment` and serialize to a
JSON file". (The symbol itself is not defined in this repo; it lives in the framework. **UNVERIFIED**
beyond this mention.)

---

## 2. `Package.swift` — platforms, products, targets

`Package.swift` is 65 lines, quoted essentially in full:

```swift
// swift-tools-version: 6.2                                    // Package.swift:13
import PackageDescription

let package = Package(
  name: "foundation-models-utilities",
  platforms: [
    .macOS("27.0"),                                            // Package.swift:19
    .iOS("27.0"),                                              // Package.swift:20
    .visionOS("27.0"),                                         // Package.swift:21
    .watchOS("27.0")                                           // Package.swift:22
  ],
  products: [
    .library(
      name: "FoundationModelsUtilities",
      targets: ["FoundationModelsUtilities"]
    )
  ],
  targets: [
    .target(
      name: "FoundationModelsUtilities",
      dependencies: [],                                        // Package.swift:33 — ZERO dependencies
      swiftSettings: [
        .enableExperimentalFeature("InternalImportsByDefault"),      // Package.swift:35
        .enableExperimentalFeature("NonisolatedNonsendingByDefault"),// Package.swift:36
        .enableUpcomingFeature("MemberImportVisibility")             // Package.swift:37
      ]
    ),
    .testTarget(name: "FoundationModelsUtilitiesTests", …),          // Package.swift:40
    .testTarget(name: "FoundationModelsUtilitiesIntegrationTests", …)// Package.swift:51
  ],
  swiftLanguageModes: [.v6]                                    // Package.swift:63
)
```

Key observations:

- **Swift tools 6.2**, **Swift 6 language mode** enforced package-wide (`swiftLanguageModes: [.v6]`).
- **Zero external dependencies.** `FoundationModels` is a system framework — no SwiftPM declaration
  is needed. The `foundation-models-language-model-protocol` skill states this explicitly:
  "`FoundationModels` is a system framework — no SwiftPM dependency declaration needed; just
  `import FoundationModels`." (`skills/foundation-models-language-model-protocol/SKILL.md:710`).
- **`InternalImportsByDefault`** is why every source file must annotate its imports `public import`
  or `private import` (e.g. `ChatCompletionsLanguageModel.swift:12` `public import Foundation`).
- **No `traits:`** declared. See §7 — the utilities SKILL.md claims SwiftPM traits exist; they do not.
- **No `.linux` platform entry** — SwiftPM has no such platform key, so absence proves nothing either
  way; see §6 for the actual Linux evidence.
- Two separate test targets: unit (`FoundationModelsUtilitiesTests`) and live
  (`FoundationModelsUtilitiesIntegrationTests`).

### Version-resolution gotcha (real, verified)

`README.md:30` instructs consumers to write:

```swift
.package(url: "https://github.com/apple/foundation-models-utilities", from: "1.0.0")
```

But the only tags that exist are `1.0.0-beta1` and `1.0.0-beta3` (`git ls-remote --tags`). SwiftPM's
`from: "1.0.0"` excludes prereleases, so **this dependency line currently resolves to nothing**.
A consumer must pin `exact: "1.0.0-beta3"` (or a branch/revision) until a stable tag ships.

---

## 3. `ChatCompletionsLanguageModel` — the worked `LanguageModel` conformance

File: `Sources/FoundationModelsUtilities/LanguageModels/ChatCompletionsLanguageModel.swift` (953 lines).

### 3.1 Imports and conditional compilation

```swift
public import Foundation                       // :12
#if canImport(FoundationNetworking)            // :13
public import FoundationNetworking             // :14
#endif                                         // :15
public import FoundationModels                 // :16
#if canImport(CoreImage)                       // :17
private import CoreImage                       // :18
private import UniformTypeIdentifiers          // :19
#endif                                         // :20
```

`FoundationNetworking` is the swift-corelibs-foundation split-out module that exists **only on
non-Darwin platforms** (Linux/Windows). Its presence at `:13-15` is the single strongest
machine-checkable signal of Linux intent in the entire package.

### 3.2 The public type

```swift
public struct ChatCompletionsLanguageModel: Sendable, LanguageModel {   // :39
  public var name: String                                              // :42
  public var url: URL                                                  // :47
  public var additionalHeaders: [String: String]                       // :52
  public var supportsGuidedGeneration: Bool                            // :54
  var urlSession: URLSession?                                          // :57 (internal — test seam)
```

`ChatCompletionsLanguageModel.swift:56` comments the `urlSession` seam:
`// Overridden in tests to inject a URLSession with mock protocol handlers.`
Tests use it directly at `ChatCompletionsTestUtilities.swift:33` (`model.urlSession = URLSession(configuration: config)`).

### 3.3 Initializer (exact, current)

```swift
public init(                                    // ChatCompletionsLanguageModel.swift:73
  name: String,
  url: URL,
  additionalHeaders: [String: String] = [:],
  supportsGuidedGeneration: Bool = true,
  urlSessionConfiguration: URLSessionConfiguration? = nil     // :78 — added in beta3
) {
  self.name = name
  self.url = url
  self.additionalHeaders = additionalHeaders
  self.supportsGuidedGeneration = supportsGuidedGeneration
  self.urlSession = urlSessionConfiguration.map { URLSession(configuration: $0) }   // :84
}
```

Beta-1 → beta-3 delta: `urlSessionConfiguration` is new (`git show 376ca60`). Its documented purpose
(`:69-72`): "Use this to tune timeouts, proxies, or other transport settings. When `nil`, an
ephemeral configuration is used." The live integration test exercises it with 300s/600s timeouts
(`ChatCompletionsLiveTests.swift:44-54`).

### 3.4 Capabilities — how they are declared

```swift
// Implementation of LanguageModel Protocol
public var capabilities: LanguageModelCapabilities {           // :88
  if supportsGuidedGeneration {
    LanguageModelCapabilities([.vision, .toolCalling, .reasoning, .guidedGeneration])   // :90
  } else {
    LanguageModelCapabilities([.vision, .toolCalling, .reasoning])                      // :92
  }
}
```

- `.vision`, `.toolCalling`, `.reasoning` are declared **unconditionally**; `.guidedGeneration` is
  gated on the `supportsGuidedGeneration` flag.
- **Beta-3 API change:** the initializer label was dropped. Beta 1 read
  `LanguageModelCapabilities(capabilities: [...])`; beta 3 reads `LanguageModelCapabilities([...])`
  (`git show 376ca60`). The labeled form still compiles — test mocks use it:
  `MockModel.swift:31` `LanguageModelCapabilities(capabilities: [.toolCalling])`. So **both
  initializers exist** in beta 3.
- Capability membership is testable via `contains`: `ChatCompletionsTests+Configuration.swift:42-45`
  asserts `model.capabilities.contains(.vision)` etc.

**What the framework does with capabilities** (Apple's own words,
`skills/foundation-models-language-model-protocol/SKILL.md:35`):

> "If a developer asks for a capability you didn't declare (e.g. tool calling on a model that doesn't
> support it), the framework throws `unsupportedCapability` for you — you don't write defensive code
> for that."

and `SKILL.md:312`: "Don't declare a capability you don't fully support — the framework throws
`unsupportedCapability` for the developer when they request a capability you didn't list."

### 3.5 `executorConfiguration` and the `Configuration` type

```swift
public var executorConfiguration: Executor.Configuration {     // :96
  Executor.Configuration(
    modelName: name,
    url: url,
    additionalHeaders: additionalHeaders,
    urlSession: urlSession
  )
}
```

```swift
public struct Executor: LanguageModelExecutor {                // :187
  public typealias Model = ChatCompletionsLanguageModel        // :188
  private let configuration: Configuration                     // :189

  public init(configuration: Configuration) {                  // :191  ← note: NOT `throws` here
    self.configuration = configuration
  }

  public struct Configuration: Hashable, Sendable {            // :195
    fileprivate let modelName: String                          // :196
    fileprivate let url: URL                                   // :197
    fileprivate let additionalHeaders: [String: String]        // :198
    fileprivate let urlSession: URLSession?                    // :199

    public static func == (lhs: Configuration, rhs: Configuration) -> Bool {   // :201
      lhs.modelName == rhs.modelName
        && lhs.url == rhs.url
        && lhs.additionalHeaders == rhs.additionalHeaders
    }

    public func hash(into hasher: inout Hasher) {              // :207
      hasher.combine(modelName)
      hasher.combine(url)
      hasher.combine(additionalHeaders)
    }
  }
```

**This is the single most instructive detail in the file.** `Hashable` is implemented **manually and
deliberately excludes `urlSession`** from both `==` and `hash(into:)`. Why it matters, in Apple's
words (`SKILL.md:65`):

> "`MyLanguageModel.Executor.Configuration: Hashable & Sendable` — Snapshot of everything the executor
> needs. **The framework caches one executor per unique configuration, so equality matters** — only put
> Hashable primitives in here."

and the pitfall (`SKILL.md:814`): "**Configuration must hold only Hashable primitives.** Don't put
opaque store objects or class references in there — the framework hashes Configuration to cache
executors."

The manual conformance is therefore a workaround: `URLSession` is a class with reference identity, so
including it would make two otherwise-identical models produce distinct cache keys (or fail to
synthesize `Hashable` at all). Note the consequence: **two models differing only in
`urlSessionConfiguration` compare equal**, so the framework may hand back a cached executor built
with the *other* session. That is a latent correctness wrinkle — see §10.

Also note `init(configuration:)` here is **non-throwing** (`:191`) while the protocol declares
`init(configuration: Configuration) throws` (`SKILL.md:51`). Swift permits a non-throwing witness for
a `throws` requirement, so this conforms; test mocks use the `throws` form
(`MockModel.swift:62`, `SkillsTests.swift:619`).

### 3.6 `prewarm` — NOT implemented here

The protocol declares:

```swift
func prewarm(model: Model, transcript: Transcript)  // default no-op    // SKILL.md:57
```

`ChatCompletionsLanguageModel.Executor` does **not** implement `prewarm`. Neither do the two test
mocks (`MockModelExecutor`, `SkillsMockModelExecutor`). It relies on the protocol's default no-op.
(grep for `prewarm` across the repo returns only `SKILL.md:57`.) So for a network-backed model,
prewarming is simply skipped — reasonable, since there is no KV cache to warm locally.

### 3.7 `respond(to:model:streamingInto:)` — the full signature and body

```swift
public func respond(                                            // :214
  to request: LanguageModelExecutorGenerationRequest,
  model: ChatCompletionsLanguageModel,
  streamingInto channel: LanguageModelExecutorGenerationChannel
) async throws {
```

Header construction (`:220-228`) — **caller headers win on collision**:

```swift
// Caller-supplied headers override the defaults on conflict.
let headers = [
  "Content-Type": "application/json",
  "Accept": "text/event-stream",
  "User-Agent": Bundle.main.bundleIdentifier ?? "com.apple.FoundationModels"   // :224
].merging(
  configuration.additionalHeaders,
  uniquingKeysWith: { _, custom in custom }                                    // :227
)
```

The `User-Agent` fallback string `"com.apple.FoundationModels"` at `:224` is notable — an app without
a bundle identifier (e.g. a Linux server binary, or a SwiftPM test process) identifies itself to the
remote endpoint as Apple's framework.

Client construction (`:230-235`): `configuration.urlSession ?? URLSession(configuration: .ephemeral)`.

Request translation (`:238-271`) — how each `request` field is consumed:

| Framework field | Wire field | Line |
|---|---|---|
| `configuration.modelName` | `model` | :239 |
| `convertedTranscript(request.transcript)` | `messages` | :240 |
| `request.generationOptions.temperature` | `temperature` | :241 |
| `request.generationOptions.samplingMode.map(topP)` | `top_p` | :242 |
| `request.generationOptions.maximumResponseTokens` | `max_completion_tokens` | :243 |
| `request.enabledToolDefinitions` | `tools` | :244-252 |
| `request.generationOptions.toolCallingMode?.kind` | `tool_choice` | :253-262 |
| `request.schema` | `response_format` | :263-270 |

Tool-choice mapping, verbatim (`:254-261`):

```swift
mode: {
  switch request.generationOptions.toolCallingMode?.kind {
  case .allowed, .none: .auto
  case .required: .required
  case .disallowed: .none
  @unknown default: .auto
  }
}()
```

Note `.none` here is `Optional.none` (i.e. `toolCallingMode == nil`) matched in the same case as
`.allowed` — both map to `auto`.

Response-format mapping (`:263-270`):

```swift
responseFormat: request.schema.map { schema in
  ChatCompletionsClient.ResponseFormat(
    jsonSchema: ChatCompletionsClient.ResponseFormat.JSONSchemaWrapper(
      name: schema.name,                    // :266 — beta3: was `schema.title` (a JSON-decoding hack)
      schema: schema
    )
  )
}
```

**Beta-3 API change, verified via `git show 376ca60`:** beta 1 had a private
`extension GenerationSchema { var title: String }` that round-tripped the schema through
`JSONEncoder`/`JSONSerialization` and read the `"title"` key, falling back to `"type"`, then to
`"Response"`. Beta 3 **deleted that extension entirely** in favour of a new first-class
**`GenerationSchema.name`** property. This is a concrete new framework API not otherwise documented.

`ContextOptions` is **never read** by this executor. `request.contextOptions` (with
`includeSchemaInPrompt` and `reasoningLevel`, per `SKILL.md:271` and `:283`) is documented in the
skill but ignored in this implementation. Likewise `request.id` and `request.metadata` are unused.

### 3.8 Sampling-mode translation and the errors it throws

```swift
private func topP(_ sampling: GenerationOptions.SamplingMode) throws -> Double {   // :367
  switch sampling.kind {
  case .greedy:
    return 0                                                                        // :370
  case .randomTopK:
    throw ChatCompletionsLanguageModel.RequestError.invalidRequest(
      "Top K sampling is not supported"                                             // :374
    )
  case .randomProbabilityThreshold(let threshold, let seed):
    guard seed == nil else {
      throw ChatCompletionsLanguageModel.RequestError.invalidRequest(
        "Setting a random seed is not supported"                                    // :379
      )
    }
    return threshold                                                                // :382
  @unknown default:
    throw ChatCompletionsLanguageModel.RequestError.invalidRequest(
      "Unknown sampling mode \(sampling.kind) is not supported"                     // :385
    )
  }
}
```

**Beta-3 renames confirmed by diff:** `.top` → `.randomTopK`, `.nucleus` →
`.randomProbabilityThreshold`. Also note `.greedy` maps to `top_p = 0`, not `temperature = 0` —
the skill's illustrative code (`SKILL.md:295`) suggests `temperature = 0` for `.greedy`; the real
implementation sets `top_p`. Divergence worth flagging.

Also note: the switch is on `sampling.kind`, the new readable projection described at `SKILL.md:288`:
"Several framework option types are enum-like structs you can *construct* but historically couldn't
*read*. To let executors translate them, there is now a `kind` property on each."

### 3.9 Streaming: `processChunks` — transcript-entry coalescing

```swift
private static func processChunks<ChunkSequence: AsyncSequence>(          // :280
  _ chunks: ChunkSequence,
  into channel: LanguageModelExecutorGenerationChannel
) async throws where ChunkSequence.Element == ChatCompletionsClient.ChatCompletionChunk {
```

The three-stable-entryID trick, with Apple's own explanatory comment verbatim (`:291-294`):

```swift
// Stable entryIDs per event type for the duration of this stream.
// Without these, interleaved reasoning/response/toolCalls chunks would
// split into multiple transcript entries — the framework only coalesces
// consecutive events of the same type into the trailing entry.
let responseEntryID  = UUID().uuidString      // :295
let reasoningEntryID = UUID().uuidString      // :296
let toolCallsEntryID = UUID().uuidString      // :297
```

This is a **framework behavior fact** stated nowhere else: *the framework coalesces only consecutive
events of the same type into the trailing entry*. It is directly test-covered:
`ChatCompletionsTests+Reasoning.swift:64-95` interleaves `reasoning / text / reasoning / text` and
asserts exactly **one** reasoning entry (`reasoningText == "First thought"`) and **one** response
entry (`responseText == "Hello world"`).

Tool-call routing, with the latching comment (`:285-289`):

```swift
// Per-index `id`/`name` for tool calls. The first delta for a given
// index supplies them; later deltas at the same index typically carry
// only argument fragments and are routed using these latched values.
// Argument accumulation is the framework's job — we just forward each
// delta via `.appendArguments`.
var toolCallRouting: [Int: (id: String, name: String)] = [:]      // :289
```

```swift
for toolCallDelta in toolCallDeltas {                             // :311
  let existing = toolCallRouting[toolCallDelta.index] ?? (id: "", name: "")
  let routing = (
    id:   existing.id   + (toolCallDelta.id ?? ""),               // :314
    name: existing.name + (toolCallDelta.function?.name ?? "")    // :315
  )
  toolCallRouting[toolCallDelta.index] = routing
  guard !routing.id.isEmpty, !routing.name.isEmpty else { continue }   // :319
  await channel.send(
    .toolCalls(
      entryID: toolCallsEntryID,
      action: .toolCall(
        id: routing.id, name: routing.name,
        action: .appendArguments(toolCallDelta.function?.arguments ?? "", tokenCount: 1)  // :327
      )
    )
  )
}
```

Note `+` (string concatenation) rather than `??` for latching id/name — so a server that streams the
id in fragments accumulates correctly, but a server that **repeats** the full id on every delta would
produce `"call_1call_1call_1"`. Worth flagging as fragile. Also note the `else if` at `:335`:
**tool-call deltas suppress text content in the same chunk** — a chunk carrying both `tool_calls` and
`content` drops the `content`.

Usage handling, with the ordering rationale verbatim (`:345-346`):

```swift
// Send usage AFTER content so the authoritative cumulative total
// overwrites any tokens credited by `appendText` for this chunk.
if let usage = chunk.usage {                                      // :347
  await channel.send(
    .response(
      entryID: responseEntryID,
      action: .updateUsage(
        input: .init(
          totalTokenCount:  usage.promptTokens,
          cachedTokenCount: usage.promptTokensDetails?.cachedTokens ?? 0        // :354
        ),
        output: .init(
          totalTokenCount:      usage.completionTokens,
          reasoningTokenCount:  usage.completionTokensDetails?.reasoningTokens ?? 0  // :358
        )
      )
    )
  )
}
```

Every `appendText`/`appendArguments` call in this file passes `tokenCount: 1` — a placeholder, since
the executor cannot tokenize. The authoritative `updateUsage` overwrites it. This is corroborated by
the test `reports final cumulative tokens when usage streams with each chunk`
(`ChatCompletionsTests+UsageReporting.swift:108-139`), whose comment reads: "The framework treats
updateUsage as wholesale replacement, so the final reported usage should reflect the last cumulative
value." Assertions: three chunks with completion counts 1, 2, 3 → final `output.totalTokenCount == 3`.

### 3.10 `convertedTranscript` — transcript → chat-completions messages

`convertedTranscript(_:)` at `:390`, signature:

```swift
private func convertedTranscript(
  _ entries: some Collection<Transcript.Entry>
) throws -> [ChatCompletionsClient.ChatMessage]
```

Nested `convertedSegment(_:in:)` at `:395` handles `Transcript.Segment`:

| Segment case | Behavior | Line |
|---|---|---|
| `.text(let text)` | `MessageContent(text: text.content)` | :400-405 |
| `.structure(let structure)` | `MessageContent(text: structure.content.jsonString)` — "Structured content is serialized to JSON text on the wire." | :406-412 |
| `.attachment(.image)` | Darwin: `image.cgImage.jpegData().base64EncodedString()` → `data:image/jpeg;base64,…`. Non-Darwin: requires `image.url` | :413-441 |
| `.attachment(@unknown)` | throws `LanguageModelError.unsupportedTranscriptContent` | :442-449 |
| `.custom` | throws `LanguageModelError.unsupportedTranscriptContent`, "Custom segments are not supported by \(Self.self)" | :450-456 |
| `@unknown default` | throws `LanguageModelError.unsupportedTranscriptContent` | :458-464 |

The **exact** `LanguageModelError` construction pattern (`:450-456`):

```swift
case .custom:
  throw LanguageModelError.unsupportedTranscriptContent(
    LanguageModelError.UnsupportedTranscriptContent(
      unsupportedContent: [entry],
      debugDescription: "Custom segments are not supported by \(Self.self)"
    )
  )
```

Non-Darwin image path (`:422-441`), new in beta 3 — the guard is the interesting part:

```swift
#else
guard let url = image.url else {                                  // :423
  throw LanguageModelError.unsupportedTranscriptContent(
    LanguageModelError.UnsupportedTranscriptContent(
      unsupportedContent: [entry],
      debugDescription: "Image attachment without a URL is not supported by \(Self.self) on this platform."
    )
  )
}
let dataURL: URL
if url.scheme == "data" {
  dataURL = url
} else {
  let data = try Data(contentsOf: url)                            // :435
  let base64String = data.base64EncodedString()
  dataURL = URL(string: "data:image/jpeg;base64,\(base64String)")!
}
```

**Beta-3 framework change deduced from the diff:** `Transcript.ImageAttachment.url` went from
non-Optional (`image.url.scheme` in beta 1) to **Optional** (`guard let url = image.url` in beta 3).

Entry-level translation loop (`:481-558`), with reasoning buffering (`:468-478`):

```swift
var messages: [ChatCompletionsClient.ChatMessage] = []
// Reasoning entries are buffered and attached to the next assistant
// message (response or toolCalls) via `reasoning_content`. If a turn
// has only reasoning with no following assistant entry, it's emitted
// as a standalone assistant message.
var pendingReasoning: String? = nil                               // :473

func consumePendingReasoning() -> String? {                       // :475
  defer { pendingReasoning = nil }
  return pendingReasoning
}
```

| `Transcript.Entry` case | Emitted message | Line |
|---|---|---|
| `.instructions` | `role: .system`, all segments | :483-490 |
| `.prompt` | flushes orphaned reasoning as a standalone `assistant` msg first (`:494-501`), then `role: .user` | :492-507 |
| `.toolCalls` | `role: .assistant` with `tool_calls` array + `reasoningContent: consumePendingReasoning()` | :509-525 |
| `.toolOutput` | `role: .tool`, `toolCallID: toolOutput.id` | :527-535 |
| `.response` | `role: .assistant` + `reasoningContent: consumePendingReasoning()` | :537-545 |
| `.reasoning` | **buffers** text into `pendingReasoning`, emits nothing | :547-553 |
| `@unknown default` | `continue` (silently skipped) | :555-556 |

Trailing flush (`:560-568`): "Trailing reasoning with no following assistant entry — emit it solo."

Tool-call serialization (`:514-522`): `call.id`, `call.toolName`, `call.arguments.jsonString`.
Tool-output keying (`:533`): `toolCallID: toolOutput.id` — i.e. the tool-output entry's own `id`
doubles as the originating call id.

Reasoning round-trip is directly tested:
- `ChatCompletionsTests+Reasoning.swift:97-130` — after two turns, the assistant message in request 2
  carries `reasoning_content == "Carefully considering"` and `content == "First answer"`.
- `ChatCompletionsTests+Reasoning.swift:132-170` — reasoning arriving *before* tool calls is attached
  to the assistant **tool-calls** message's `reasoning_content`.

### 3.11 Error types

```swift
public struct APIError: LocalizedError {                          // :109
  public var message: String                                      // :111
  public var type: String?                                        // :115
  public var param: String?                                       // :119
  public var code: String?                                        // :123
  public init(message: String, type: String? = nil, param: String? = nil, code: String? = nil)  // :131
}
```

```swift
public enum RequestError: LocalizedError {                        // :146
  case invalidRequest(_ description: String)                      // :149
  case invalidStreamData                                          // :151
  case httpError(statusCode: Int, data: Data)                     // :156

  public var errorDescription: String? {                          // :158
    switch self {
    case .invalidRequest(let description): "Invalid request: \(description)"
    case .invalidStreamData: "Invalid streaming data received"
    case .httpError(let statusCode, let data):
      """
      HTTP error with status code \(statusCode):
      \(String(data: data, encoding: .utf8) ?? data.description)
      """
    }
  }
}
```

Internal wire type `ErrorResponse` at `:176-185` decodes `{"error": {...}}` envelopes.

**Which error is thrown when:**

| Condition | Thrown | Line |
|---|---|---|
| Top-K sampling requested | `RequestError.invalidRequest("Top K sampling is not supported")` | :373 |
| Random seed set | `RequestError.invalidRequest("Setting a random seed is not supported")` | :378 |
| Unknown sampling mode | `RequestError.invalidRequest("Unknown sampling mode …")` | :384 |
| Non-200 HTTP (Darwin) | `RequestError.httpError(statusCode:data:)` | :592 |
| Non-200 HTTP (non-Darwin) | `RequestError.httpError(statusCode:data:)` | :610 |
| SSE `data:` payload not UTF-8 | `RequestError.invalidStreamData` | :666 |
| SSE payload decodes as error envelope | `APIError(message:type:param:code:)` | :677 |
| Custom / unknown / unsupported segment | `LanguageModelError.unsupportedTranscriptContent` | :424, :443, :451, :459 |

Notably absent: this executor **never** throws `.rateLimited`, `.contextSizeExceeded`,
`.guardrailViolation`, `.timeout`, or any other typed `LanguageModelError` case — even a 429 becomes
a generic `RequestError.httpError`. The `foundation-models-language-model-protocol` skill explicitly
tells third parties to do better (`SKILL.md:545`, `:550`). The test only asserts
`#expect(throws: (any Error).self)` for a 429 (`ChatCompletionsTests+ErrorHandling.swift:21-30`),
so the weak typing is baked into the tests too.

### 3.12 The private `ChatCompletionsClient` and the SSE parser

```swift
private struct ChatCompletionsClient {                            // :575
  let baseURL: URL
  let headers: [String: String]
  let session: URLSession
```

`streamChatCompletions(request:)` at `:580` returns `AsyncThrowingStream<ChatCompletionChunk, Swift.Error>`
and forks on platform (`:587` `#if canImport(Darwin)`):

- **Darwin:** `try await session.bytes(for: urlRequest)` → true incremental streaming via
  `for try await line in stream.lines` (`:598`). Non-200 drains the byte stream into `Data` for the
  error payload (`:594`).
- **Non-Darwin:** `try await session.data(for: urlRequest)` (`:606`) → **buffers the entire response**,
  then splits on `\n` (`:617`). **Linux gets no incremental streaming**; tokens arrive all at once
  when the request completes. This is the most consequential portability difference in the package.

Both branches do `response as! HTTPURLResponse` (`:589`, `:607`) — a force cast that would trap on a
non-HTTP response.

`continuation.onTermination = { _ in task.cancel() }` (`:630`) is the only cancellation handling;
there is no `try Task.checkCancellation()` inside the loop, despite `SKILL.md:637-648` instructing
implementers to add one.

SSE line parser (`:650-689`):

```swift
func parseStreamLine(_ line: String) throws -> ChatCompletionChunk? {
  let trimmedLine = line.trimmingCharacters(in: .whitespaces)
  // Skip empty lines and comments
  guard !trimmedLine.isEmpty, !trimmedLine.hasPrefix(":") else { return nil }   // :654
  if trimmedLine.hasPrefix("data: ") {
    let jsonString = String(trimmedLine.dropFirst(6))  // Remove "data: "       // :659
    if jsonString.trimmingCharacters(in: .whitespaces) == "[DONE]" { return nil }  // :661
    guard let jsonData = jsonString.data(using: .utf8) else {
      throw ChatCompletionsLanguageModel.RequestError.invalidStreamData         // :666
    }
    let decoder = JSONDecoder()
    do { return try decoder.decode(ChatCompletionChunk.self, from: jsonData) }
    catch {
      if let response = try? decoder.decode(ChatCompletionsLanguageModel.ErrorResponse.self, from: jsonData) {
        throw ChatCompletionsLanguageModel.APIError(…)                          // :677
      }
      throw error
    }
  }
  return nil    // non-`data:` field lines (event:, id:, retry:) silently ignored  // :688
}
```

Edge cases all test-covered in `ChatCompletionsTests+SSEEdgeCases.swift`: comment lines (`:21`),
multiple blank lines (`:43`), `data:  [DONE]` with extra whitespace (`:65`), and
`event:` / `id:` / `retry:` field lines (`:83`).

Note: `hasPrefix("data: ")` requires **exactly one space**. A server emitting `data:{"…"}` (no space,
legal per the SSE spec) is silently dropped — the line falls through to `return nil` at `:688`. Not
tested. Flagged as a likely interop bug.

### 3.13 Wire format types (request)

`ChatCompletionRequest` (`:691-738`) with `CodingKeys` (`:726-737`):

```swift
var model: String                     // "model"
var messages: [ChatMessage]           // "messages"
var temperature: Double?              // "temperature"
var topP: Double?                     // "top_p"
var maxCompletionTokens: Int?         // "max_completion_tokens"
var tools: [Tool]?                    // "tools"
var toolChoice: ToolChoice?           // "tool_choice"
var responseFormat: ResponseFormat?   // "response_format"
var stream = true                     // "stream"            :715 — ALWAYS true
var streamOptions = StreamOptions(includeUsage: true)   // "stream_options"  :716 — ALWAYS on
```

`stream: true` and `stream_options: {"include_usage": true}` are **non-configurable defaults**
(`:715-716`). Tested at `ChatCompletionsTests+RequestFormat.swift:34-42` and
`ChatCompletionsTests+UsageReporting.swift:21-31`.

`ChatMessage` has a hand-written `encode(to:)` (`:776-793`) implementing a **content-compaction rule**:

```swift
let hasToolCalls  = toolCalls?.isEmpty == false
let compactText   = content.count == 1 ? content.first?.text : nil       // :782

if let compactText {
  try container.encode(compactText, forKey: .content)                    // :785 — plain string
} else if !hasToolCalls && !content.isEmpty {
  try container.encode(content, forKey: .content)                        // :787 — array of blocks
}
```

So a single text segment is sent as a bare JSON **string** (maximum server compatibility), while
multi-part / image content is sent as an **array of content blocks**. And a message with tool calls
omits `content` entirely. Tested implicitly at `ChatCompletionsTests+Reasoning.swift:129`
(`assistantMessage["content"] as? String == "First answer"` — a `String`, not an array).

Other wire types: `Tool` (`:796`, `type = "function"`), `ToolCall` (`:807`),
`ResponseFormat` (`:818`, `type = "json_schema"`, `strict = true` at `:831`),
`MessageContent` (`:902`, with `ContentType.text` / `.imageURL`, and `ImageURL.detail = "auto"` at `:920`).

`ChatCompletionChunk` (`:835-900`) decodes `id`, `model`, `choices`, `usage`, with
`Delta` fields `role`, `content`, `reasoning_content`, `tool_calls`, and `ToolCallDelta`
(`index`, `id`, `type`, `function{name, arguments}`). `Usage` decodes `prompt_tokens`,
`completion_tokens`, `prompt_tokens_details.cached_tokens`,
`completion_tokens_details.reasoning_tokens`.

`CGImage.jpegData()` helper at `:937-952`, guarded `#if canImport(CoreImage)`, uses
`CGImageDestinationCreateWithData` + `UTType.jpeg` and **force-unwraps the destination** (`:946`).

---

## 4. Assignment item (e) — the `buildURLRequest` verdict: **CONFIRMED, NOT FIXED**

Forum thread 838444's report is **accurate**. Verbatim source:

```swift
  private func buildURLRequest(for request: ChatCompletionRequest) throws -> URLRequest {   // :634
    let isVersioned = baseURL.pathComponents.contains("v1")                                 // :635
    let endpoint = isVersioned ? "/chat/completions" : "/v1/chat/completions"                // :636
    let url = baseURL.appendingPathComponent(endpoint)                                       // :637
    var urlRequest = URLRequest(url: url)
    urlRequest.httpMethod = "POST"
    for (header, value) in headers {
      urlRequest.setValue(value, forHTTPHeaderField: header)
    }

    let encoder = JSONEncoder()
    urlRequest.httpBody = try encoder.encode(request)

    return urlRequest
  }
```
— `Sources/FoundationModelsUtilities/LanguageModels/ChatCompletionsLanguageModel.swift:634-648`

**Never fixed.** `git log -p --all -S "pathComponents.contains" -- Sources/` returns exactly one hit,
the introducing commit `a047a503`. The line is byte-identical in `1.0.0-beta1` and `1.0.0-beta3`;
`git show 376ca60` shows no change to `buildURLRequest`.

**Empirically reproduced** (ran the exact two lines against Swift 6.3.3 Foundation on macOS):

| Base URL | `pathComponents` | Resulting endpoint | OK? |
|---|---|---|---|
| `https://api.openai.com/v1` | `["/", "v1"]` | `https://api.openai.com/v1/chat/completions` | ✅ |
| `http://localhost:8000` | `[]` | `http://localhost:8000/v1/chat/completions` | ✅ |
| `http://127.0.0.1:11434/v1` (Ollama) | `["/", "v1"]` | `http://127.0.0.1:11434/v1/chat/completions` | ✅ |
| `https://api.example.com/` | `["/"]` | `https://api.example.com/v1/chat/completions` | ✅ |
| **`https://generativelanguage.googleapis.com/v1beta/openai`** | `["/", "v1beta", "openai"]` | `…/v1beta/openai/**v1**/chat/completions` | ❌ |
| **`https://api.example.com/v2`** | `["/", "v2"]` | `https://api.example.com/v2/**v1**/chat/completions` | ❌ |
| **`https://api.example.com/v3`** | `["/", "v3"]` | `https://api.example.com/v3/**v1**/chat/completions` | ❌ |
| **`https://x.openai.azure.com/openai/deployments/gpt4`** | `["/","openai","deployments","gpt4"]` | `…/gpt4/**v1**/chat/completions` | ❌ |

Root cause: `"v1"` is treated as the *only* recognized version segment, and the fallback is
**unconditional path injection** rather than "append nothing". Any server whose base path already
terminates at its API root but is versioned as `v1beta`, `v2`, `v3`, or not versioned by path at all
(Azure deployments) receives a spurious `/v1`. There is **no escape hatch** — `buildURLRequest` is
`private`, and no initializer parameter overrides the path.

**Workaround available today:** include a literal `v1` path component in the base URL, since the
check is `contains`, not a suffix check. E.g. `https://api.example.com/api/v1` →
`https://api.example.com/api/v1/chat/completions` (verified in the table above). For a `/v2` server
there is **no workaround** short of a local reverse proxy.

**Bonus README bug found while testing:** `README.md:52` and `README.md:67` both write
`URL(string: "http://localhost/v1:8000")!` — the port is inside the path. Its `pathComponents` are
`["/", "v1:8000"]`, host is `localhost` on default port 80, and the resulting endpoint is
`http://localhost/v1:8000/v1/chat/completions`. The intended URL is `http://localhost:8000/v1`.
This malformed URL appears in the README's very first code sample.

Test coverage for the endpoint is weak enough to miss all of this — the only assertion is:

```swift
#expect(request.url?.path.hasSuffix("/chat/completions") == true)
```
— `Tests/…/LanguageModelTests/ChatCompletionsTests+RequestFormat.swift:83`

which passes for every one of the ❌ rows above.

---

## 5. Skills — mechanism and the KV-cache tradeoff

### 5.1 `Skill` — two storages

`Sources/FoundationModelsUtilities/Skills/Skill.swift`.

```swift
public struct Skill {                                             // :65
  var name: String { storage.name }                               // :66
  var description: String { storage.description }                 // :68
  func activate() { storage.onActivate() }                        // :70
  func deactivate() {                                             // :72
    if case .instructions(let skill) = storage { skill.onDeactivate() }
  }
  let storage: Storage                                            // :78

  enum Storage {                                                  // :80
    case prompt(PromptSkill)                                      // :81
    case instructions(InstructionsSkill)                          // :82
    …
  }
```

Note: `name`, `description`, `storage`, `activate()`, `deactivate()` are all **internal**, not public.
Only the initializers are public. Tests reach them via `@testable import`
(`SkillTests.swift:12`, `:23` `guard case .prompt = skill.storage`).

Backing structs (`:232-246`):

```swift
struct InstructionsSkill {                                        // :232
  let name: String
  let description: String
  let instructions: AnyDynamicInstructions                        // :235
  let allowsDeactivation: Bool                                    // :236
  let onActivate:   @Sendable () -> Void
  let onDeactivate: @Sendable () -> Void
}

struct PromptSkill {                                              // :241
  let name: String
  let description: String
  let prompt: Prompt                                              // :244
  let onActivate: @Sendable () -> Void
}
```

`AnyDynamicInstructions` (`:235`, used at `:183`, `:223`) is a framework type-eraser — **UNVERIFIED**
beyond its use here; it is not defined in this repo.

### 5.2 The four public `Skill` initializers (exact signatures)

```swift
// 1. Prompt-based, string.                                       Skill.swift:120
public init(
  name: String,
  description: String,
  prompt: String,
  onActivate: @Sendable @escaping () -> Void = {}
)

// 2. Prompt-based, @PromptBuilder.                               Skill.swift:136
public init(
  name: String,
  description: String,
  onActivate: @Sendable @escaping () -> Void = {},
  @PromptBuilder prompt: () -> Prompt,
)

// 3. Instructions-based, InstructionsRepresentable.              Skill.swift:171
public init(
  name: String,
  description: String,
  instructions: InstructionsRepresentable,
  allowsDeactivation: Bool = false,
  onActivate:   @Sendable @escaping () -> Void = {},
  onDeactivate: @Sendable @escaping () -> Void = {}
)

// 4. Instructions-based, @DynamicInstructionsBuilder.            Skill.swift:211
public init(
  name: String,
  description: String,
  allowsDeactivation: Bool = false,
  onActivate:   @Sendable @escaping () -> Void = {},
  onDeactivate: @Sendable @escaping () -> Void = {},
  @DynamicInstructionsBuilder instructions: () -> some DynamicInstructions
)
```

Initializer 1 delegates to 2 by wrapping in `Prompt { prompt }` (`Skill.swift:126-132`).
Initializer 3 wraps in `AnyDynamicInstructions(Instructions(instructions))` (`Skill.swift:183`).

**Initializer 4 is the sleeper feature.** Its doc comment (`Skill.swift:194-198`):

> "The closure may include `Instructions` content as well as `Tool` values; while the skill is active,
> its instructions are injected into the instructions entry **and any tools it carries become
> available to the model**."

So a `Skill` can gate an entire **toolset** behind a just-in-time activation — this is the calendaring
example in `Skills.swift:40-52` where activating `"calendaring"` brings
`QueryCalendarEventsTool()`, `AddCalendarEventTool()`, `DeleteCalendarEventTool()`,
`ModifyCalendarEventTool()` into scope. Test coverage:
`SkillsTests.swift:379-407` — `active builder skill with a tool renders no tool text` — proves the
tool contributes **zero text** to the instructions entry while still being registered.

### 5.3 The prompt-vs-instructions tradeoff — CONFIRMED in source

README's claims (`README.md:148-206`) verified line by line:

**Claim 1 — prompt skill content lands in a TOOL OUTPUT entry, preserving the KV cache.** ✅

```swift
func call(arguments: GeneratedContent) async throws -> Prompt {   // Skills.swift:293
  …
  switch skill.storage {
  case .prompt(let promptSkill):
    return promptSkill.prompt                                     // Skills.swift:313
  case .instructions:
    let activated = activations.isActive(skill.name)
    let verb = activated ? "deactivated" : "activated"
    return Prompt { "Successfully \(verb) skill: \(skill.name)" } // Skills.swift:317
  }
}
```

The tool's **return value becomes the tool-output transcript entry**. For a prompt skill that return
value *is the skill body*. Test: `SkillsTests.swift:20-28` asserts
`toolOutput?.segments.first?.text == "foo prompt"`. Earlier transcript bytes are untouched → prefix
KV cache intact. Source doc comment restates it (`Skill.swift:25-26`): "the skill's content is added
to the transcript as part of the matching tool output. This has the advantage of not invalidating the
key-value cache."

**Claim 2 — instructions skill content is appended into the first instructions entry, invalidating the KV cache.** ✅

```swift
if activations.isActive(skill.name) {                             // Skills.swift:156
  Instructions { "\nSkill: \(skill.name) [active]" }              // Skills.swift:157-159
  stored.instructions                                             // Skills.swift:160  ← body spliced in
} else {
  Instructions {
    "\nSkill: \(skill.name) [inactive]"
    "Description: \(skill.description)"                           // Skills.swift:163-165
  }
}
```

Because `Skills` conforms to `DynamicInstructions` and this is its `body`, activation changes the
**instructions entry at the top of the transcript** — the prefix changes, so every cached key/value
downstream is invalidated. Test proving the exact rendered text after activation
(`SkillsTests.swift:78-97`):

```
If a skill below fits the user's request, silently activate it before responding. Otherwise, respond normally without calling tools.

Skill: foo [on demand]
Description: foo description

Skill: bar [active]
bar instructions
```

Note the asymmetry: an **inactive** instructions skill shows `Description:`; an **active** one drops
the description and shows the **body** instead. The tool output for an instructions skill is only
`"Successfully activated skill: bar"` (`SkillsTests.swift:60`), matching the README's second ASCII
diagram ("skill activated message").

**Claim 3 — `allowsDeactivation: true` lets the model issue a second tool call to remove it.** ✅

- `allowsDeactivation` exists only on `InstructionsSkill` (`Skill.swift:236`); `PromptSkill` has no
  such field. Prompt skills are structurally non-deactivatable.
- `Skill.deactivate()` (`Skill.swift:72-76`) is a no-op unless storage is `.instructions`.
- The toggle branch (`Skills.swift:185-200`):

```swift
onCall: { [activations] skill in
  switch skill.storage {
  case .prompt:
    // On-demand: fire the activation callback, but don't track the skill
    // as active — there's no persistent state to toggle off later.
    skill.activate()                                              // Skills.swift:190
  case .instructions:
    if activations.isActive(skill.name) {
      activations.deactivate(skill.name)                          // Skills.swift:194
      skill.deactivate()
    } else {
      activations.activate(skill.name)                            // Skills.swift:196
      skill.activate()
    }
  }
}
```

- Test: `SkillsTests.swift:63-76` — two `respond` calls produce tool outputs
  `"Successfully activated skill: baz"` then `"Successfully deactivated skill: baz"`.

**Claim 4 (README:100) — `SkillActivations` conforms to `Observable` and `RandomAccessCollection`.** ⚠️ **HALF FALSE.**
`Observable`: true. `RandomAccessCollection`: **removed in beta 3**. See §5.5.

### 5.4 `Skills` — `DynamicInstructions` conformance and the synthesized tool

```swift
public struct Skills: DynamicInstructions {                       // Skills.swift:55

  private static let defaultInstructions = Instructions {         // Skills.swift:57
    """
    If a skill below fits the user's request, silently activate it before \
    responding. Otherwise, respond normally without calling tools.
    """
  }
```

Two public initializers, identical parameters except the last:

```swift
public init(                                                      // Skills.swift:93 (result-builder)
  activations: SkillActivations,
  toolName: String? = nil,
  toolDescription: String? = nil,
  instructions: Instructions? = nil,          // ← added in beta 3
  strictSchema: Bool = false,
  @SkillsBuilder skills: () -> [Skill]
)

public init(                                                      // Skills.swift:127 (array)
  activations: SkillActivations,
  toolName: String? = nil,
  toolDescription: String? = nil,
  instructions: Instructions? = nil,
  strictSchema: Bool = false,
  skills: [Skill]
)
```

`instructions ?? Skills.defaultInstructions` at `Skills.swift:138`. Override tested at
`SkillsTests.swift:213-227`.

The `body` (`Skills.swift:145-202`) emits, in order:
1. `instructions` (the leading text),
2. a `DynamicInstructions.ForEach(Array(skills.enumerated()), id: \.element.name)` (`Skills.swift:149`)
   rendering one block per skill,
3. the `ToggleSkillTool`.

Rendering states — three, not two (`Skills.swift:150-176`):

| Storage | Activation state | Rendered | Line |
|---|---|---|---|
| `.instructions` | active | `\nSkill: <name> [active]` + the body | :156-160 |
| `.instructions` | inactive | `\nSkill: <name> [inactive]` + `Description: <desc>` | :162-165 |
| `.prompt` | (n/a) | `\nSkill: <name> [on demand]` + `Description: <desc>` | :172-175 |

Apple's rationale for the third state, verbatim (`Skills.swift:168-171`):

> "Prompt-based skills are one-shot: invoking one injects its content as tool output rather than
> toggling a persistent mode. We label them as on-demand so the model isn't told they're 'inactive'
> after it has already invoked them."

The leading `"\n"` in each header (`:158`, `:163`, `:173`) is the beta-3 "blank line between skills"
formatting change. Tested exhaustively in `SkillsTests.swift:265-407` (six separation tests).

### 5.5 `SkillActivations`

```swift
public final class SkillActivations: Sendable, Observable {       // SkillActivations.swift:23
  private let _registrar = ObservationRegistrar()                 // :24
  private let _names = Mutex<[String]>([])                        // :25

  public init() {}                                                // :27

  public func activate(_ name: String) {                          // :29
    _registrar.withMutation(of: self, keyPath: \.activeSkillNames) {
      _names.withLock { names in
        guard !names.contains(name) else { return }
        names.append(name)
      }
    }
  }

  public func deactivate(_ name: String) {                        // :38
    _registrar.withMutation(of: self, keyPath: \.activeSkillNames) {
      _names.withLock { names in names.removeAll(where: { $0 == name }) }
    }
  }

  /// Returns whether the skill with the given name is currently active.
  public func isActive(_ name: String) -> Bool {                  // :47
    activeSkillNames.contains(name)
  }

  /// The names of all currently active skills.
  public var activeSkillNames: [String] {                         // :52
    _registrar.access(self, keyPath: \.activeSkillNames)
    return _names.withLock { $0 }
  }
}
```

**Complete public surface: `init()`, `activate(_:)`, `deactivate(_:)`, `isActive(_:)`,
`activeSkillNames`. That is all.**

- Conforms to `Observable` **manually** — not via the `@Observable` macro. It hand-rolls
  `ObservationRegistrar` + `withMutation`/`access` keyed on `\.activeSkillNames`. This is required
  because `@Observable` cannot be applied to a `final class` that must also be `Sendable` with
  `Mutex`-guarded storage.
- Thread safety via `Synchronization.Mutex` (`SkillActivations.swift:13` `import Synchronization`).
- **Does NOT conform to `RandomAccessCollection`.** Removed in `376ca60`. Both `README.md:100` and
  `skills/foundation-models-utilities/SKILL.md:150` still claim it does, and the latter even shows a
  now-broken SwiftUI snippet: `ForEach(assistant.activations, id: \.self) { name in … }`
  (`SKILL.md:158`). The correct beta-3 form is `ForEach(assistant.activations.activeSkillNames, id: \.self)`.
- `activate(_:)` is idempotent (`guard !names.contains(name)`), so repeated activation won't duplicate.

### 5.6 `ToggleSkillTool` — synthesis, naming, schema

```swift
private struct ToggleSkillTool: @unchecked Sendable, Tool {       // Skills.swift:205
  let name: String
  let description: String
  let parameters: GenerationSchema
  let onCall: @Sendable (Skill) -> Void
  let skills: [Skill]
  let activations: SkillActivations
```

**Naming rule** (`Skills.swift:221-240`):

```swift
let allowsDeactivation = skills.lazy.compactMap({ skill in
  if case .instructions(let stored) = skill.storage { return stored }
  return nil
}).contains(where: \.allowsDeactivation)                          // :226

let resolvedName = name ?? (allowsDeactivation ? "toggle_skill" : "activate_skill")   // :240
```

So the name is `"toggle_skill"` iff **any** instructions skill in the list sets
`allowsDeactivation: true`; otherwise `"activate_skill"`. Tests: `SkillsTests.swift:26` (`activate_skill`),
`SkillsTests.swift:129-135` (`toggle_skill`), `SkillsTests.swift:119-127` (custom `use_skill`).

**Schema construction and `strictSchema`** (`Skills.swift:228-283`):

```swift
let activeNames = Set(activations.activeSkillNames)               // :228

var allowed = skills
  .map(\.name)
  .filter { !activeNames.contains($0) }                           // :230-233

if !strictSchema || allowsDeactivation {
  allowed += activeNames                                          // :236
}
allowed.sort()                                                    // :237

let parameters = try! GenerationSchema(                           // :269
  root: DynamicGenerationSchema(
    name: "Arguments",
    properties: [
      DynamicGenerationSchema.Property(
        name: "skill",
        schema: DynamicGenerationSchema(
          type: String.self,
          guides: [.anyOf(allowed)]                               // :277
        ),
      )
    ]
  ),
  dependencies: []
)
```

A single `skill: String` argument constrained by `.anyOf(allowed)`. With `strictSchema: true` and no
deactivatable skill, already-active names are **excluded** from the enum, so the model literally
cannot emit an invalid toggle. Default is `strictSchema: false` (`Skills.swift:98`, `:132`).
Note the `try!` at `:269` — malformed skill names would trap.

**Default descriptions (four variants, all test-pinned)** — `Skills.swift:242-267`:

```swift
let hasOnDemandSkill = skills.contains { skill in
  if case .prompt = skill.storage { return true }
  return false
}                                                                 // :242-247

let onDemandExplanation: String? = if hasOnDemandSkill {          // :250
  """
  Skills marked [on demand] aren't toggled on or off; calling this tool \
  on one delivers its guidance once.
  """
} else { nil }

let defaultDescription = if allowsDeactivation {
  "Activate or deactivate a skill yourself when the user's request matches its description, and otherwise respond normally without calling this tool. Don't ask the user for permission to activate, and don't mention activation in your response."
    + (onDemandExplanation.map { " \($0)" } ?? "")                // :261-262
} else {
  "Activate a skill yourself when the user's request matches its description, and otherwise respond normally without calling this tool. Don't ask the user for permission to activate, and don't mention activation in your response."
    + (onDemandExplanation.map { " \($0)" } ?? "")                // :264-265
}
```

All four combinations of (`allowsDeactivation` × `hasOnDemandSkill`) are asserted verbatim at
`SkillsTests.swift:139-202`, plus the override path at `:204-211`.

**`call(arguments:)` and the unknown-skill error** (`Skills.swift:293-319`):

```swift
func call(arguments: GeneratedContent) async throws -> Prompt {
  let name = try arguments.value(String.self, forProperty: "skill")   // :294

  guard let skill = skills.first(where: { $0.name == name }) else {
    throw GeneratedContent.ParsingError(                             // :298
      rawContent: arguments.jsonString,
      debugDescription: """
        Model attempted to toggle a skill named '\(name)', \
        but no matching skill was found.

        Available skills:
        \(skills.map(\.name).joined(separator: "\n"))
        """
    )
  }

  defer { onCall(skill) }                                            // :309  ← IMPORTANT
  …
}
```

**The `defer` at `:309` is a subtle and important ordering detail.** The activation state mutation
happens *after* the return value is computed. That is why the instructions branch reads
`let activated = activations.isActive(skill.name)` and then says `activated ? "deactivated" : "activated"`
(`Skills.swift:315-316`) — the verb is **inverted** relative to the pre-call state, because the
mutation hasn't run yet. Confusing on first read, correct in effect.

`GeneratedContent.ParsingError(rawContent:debugDescription:)` (`:298`) is a framework error type used
here as the "model hallucinated a skill name" path.

### 5.7 `SkillsBuilder`

`Sources/FoundationModelsUtilities/Skills/SkillBuilder.swift` — note filename is `SkillBuilder.swift`
(singular) but the type is `SkillsBuilder` (plural).

```swift
@resultBuilder                                                    // :41
public struct SkillsBuilder {
  public static func buildBlock(_ components: [Skill]...) -> [Skill]      // :45
  public static func buildExpression(_ expression: Skill) -> [Skill]      // :51
  public static func buildExpression(_ expression: Skill?) -> [Skill]     // :57
  public static func buildEither(first component: [Skill]) -> [Skill]     // :62
  public static func buildEither(second component: [Skill]) -> [Skill]    // :67
  public static func buildArray(_ components: [[Skill]]) -> [Skill]       // :72
}
```

Six methods total. **No `buildOptional`** — optionality is handled by the
`buildExpression(_ expression: Skill?)` overload at `:57`, which is why the utilities skill notes
"There is no `Optional` flag in the API — the builder accepts a `Skill?` directly"
(`skills/foundation-models-utilities/SKILL.md:177`). Consequence: a bare `if` without `else` is
**not** supported (that requires `buildOptional`); only `if`/`else` via `buildEither`.
All six paths are covered in `SkillBuilderTests.swift` (13 tests, lines 27-202).

---

## 6. History-management profile modifiers

### 6.1 Exact signatures, every parameter, every default

```swift
// DropCompletedToolCalls.swift:38
extension LanguageModelSession.DynamicProfile {
  public func droppingCompletedToolCalls() -> some DynamicProfile
}

// RollingWindow.swift:36
extension LanguageModelSession.DynamicProfile {
  public func rollingWindow(entries: Int) -> some DynamicProfile
}

// RollingWindow.swift:64
extension LanguageModelSession.DynamicProfile {
  public func rollingWindow(size: RollingWindowSize) -> some DynamicProfile
}

// SummarizeHistory.swift:53
extension LanguageModelSession.DynamicProfile {
  public func summarizeHistory<Model: LanguageModel>(
    entryThreshold: Int,                  // no default
    model: Model,                         // no default  ← see §7 correction
    instructions: Instructions? = nil,
    summaryPostamble: String? = nil
  ) -> some DynamicProfile
}

// RollingWindow.swift:86
public enum RollingWindowSize: Sendable {
  case entries(Int)                       // only case
}
```

`droppingCompletedToolCalls()` takes **no parameters at all**. `rollingWindow(entries:)` delegates to
`rollingWindow(size: .entries(entries))` (`RollingWindow.swift:37`). `RollingWindowSize` has exactly
one case today — clearly a seam for a future `.tokens(Int)`.

**`summarizeHistory` has NO default for `model:`.** The utilities skill claims
`model: Model = SystemLanguageModel()` (`skills/foundation-models-utilities/SKILL.md:234`); the
source has no default (`SummarizeHistory.swift:55`). A generic parameter can't take a default that
would fix `Model` anyway. See §7.

### 6.2 The `DynamicProfileModifier` implementation pattern

All three share the same shape — a private struct conforming to
`LanguageModelSession.DynamicProfileModifier`, with an `@SessionProperty(\.history)` wrapper and a
`body(content:)` that returns `content.onPrompt { … }`:

```swift
private struct DropCompletedToolCallsModifier: LanguageModelSession.DynamicProfileModifier {  // :43
  @SessionProperty(\.history)                                     // :44
  private var history                                             // :45

  func body(content: Content) -> some DynamicProfile {            // :47
    content.onPrompt { … history = … }                            // :48
  }
}
```

Three framework APIs surface here that appear nowhere else in the material:
`LanguageModelSession.DynamicProfileModifier` (protocol, with associated `Content`),
**`@SessionProperty(\.history)`** (a property wrapper giving read/write access to the session's
transcript entries — assignment at `DropCompletedToolCalls.swift:65` mutates it), and
**`.onPrompt { }`** (a hook that runs before each generation).

Note the `history` type supports `lastIndex(where:)`, `prefix(upTo:)`, `suffix(from:)`, `suffix(_:)`,
`count`, `last`, and `+` concatenation with an array literal, and is assignable from
`[Transcript.Entry]` (`SummarizeHistory.swift:153`). So it behaves as a `RandomAccessCollection` of
`Transcript.Entry` with a settable projection.

### 6.3 `droppingCompletedToolCalls()` — semantics

```swift
content.onPrompt {
  let lastOutputIndex =
    history.lastIndex(where: { entry in                           // :51
      if case .response  = entry { return true }
      if case .toolCalls = entry { return true }
      return false
    }) ?? history.startIndex                                      // :55

  let prefix = history.prefix(upTo: lastOutputIndex).filter { entry in   // :57
    if case .toolCalls  = entry { return false }
    if case .toolOutput = entry { return false }
    return true
  }

  let suffix = history.suffix(from: lastOutputIndex)              // :63

  history = prefix + suffix                                       // :65
}
```

Semantics: find the index of the **last** `.response` or `.toolCalls` entry; strip all `.toolCalls`
and `.toolOutput` from everything *before* it; keep everything from it onward verbatim. Effect: the
most recent tool-call exchange survives; all earlier ones are evicted. Instructions, prompts, and
responses are always preserved.

Tests (`DroppingCompletedToolCallsTests.swift`):

- `:30-46` after one turn: `[.instructions, .prompt("first"), .toolCall("activate_skill"), .toolOutput("echoed"), .response("OK")]`
  — nothing dropped ("still 'incomplete'").
- `:48-68` after two turns: `[.instructions, .prompt("first"), .response("OK"), .prompt("second"), .toolCall(…), .toolOutput(…), .response("OK")]`
  — the *first* turn's tool pair is gone, the second's survives.

### 6.4 `rollingWindow(entries:)` — semantics and a documented bug

```swift
content.onPrompt {
  switch size {
  case .entries(let numberOfEntries):
    history = history.suffix(numberOfEntries)                     // :79
  }
}
```

A naive `suffix(n)`. It is **not transcript-aware** — it will happily cut between a prompt and its
response, and it can drop the `.instructions` entry. The tests document this explicitly.

`RollingWindowTests.swift:60-81`, comment verbatim (`:71-73`):

> "The naive suffix(2) trim repeatedly cuts between a prompt and its response, so the window starts
> with an orphaned response. **This documents the (buggy) naive outcome; in practice it crashes
> partway through.**"

Expected value asserted (`:74-80`):

```swift
session.transcriptSummary == [
  .instructions,
  .response("OK"),        // ← orphaned response, no preceding prompt
  .prompt("fourth"),
  .response("OK")
]
```

This is Apple shipping a **known-buggy** modifier with a test that pins the buggy behavior and a
comment admitting "in practice it crashes partway through." Strong signal for the "emerging and
experimental" framing. Interesting secondary observation: `.instructions` survives at index 0 even
with `windowSize: 2`, so the framework must re-materialize the instructions entry after the modifier
runs (the modifier itself has no logic to preserve it). **UNVERIFIED** mechanism.

### 6.5 `summarizeHistory(entryThreshold:model:instructions:summaryPostamble:)` — semantics

```swift
content.onPrompt {
  guard history.count > entryThreshold else { return }            // :99  ← strict >
  guard case .prompt(let prompt) = history.last else { return }    // :103 ← trailing entry MUST be a prompt

  let session = LanguageModelSession(
    model: model,
    instructions: { instructions ?? Instructions { <default summarizer prompt> } }   // :107-132
  )

  let textRepresentation = history.chatLog()                      // :134

  let summary = try await session.respond(
    to: Prompt { "Summarize this conversation:\n\n\(textRepresentation)" }   // :136-140
  ).content

  let postamble = summaryPostamble ?? Self.defaultSummaryPostamble          // :142
  var summaryContent = """
    Summary of the conversation so far:
    \(summary)
    """
  if !postamble.isEmpty { summaryContent += "\n\n\(postamble)" }   // :147-149
  summaryContent += "\n\n"                                        // :150
  let summarySegment = Transcript.TextSegment(content: summaryContent)

  history = [                                                     // :153
    .prompt(
      Transcript.Prompt(
        id: UUID().uuidString,
        segments: [.text(summarySegment)] + prompt.segments,      // :158
        options: prompt.options,
        responseFormat: prompt.responseFormat
      )
    )
  ]
}
```

**Trigger condition (definitive): `history.count > entryThreshold` — an ENTRY COUNT, strictly greater.
There is no token counting anywhere in this file, or anywhere in the package.**

Second gate: `history.last` must be a `.prompt`. If the hook fires on a tool-output continuation, it
is a **no-op**. Test `only summarizes on prompts, not on tool-output continuations`
(`SummarizeHistoryTests.swift:155-189`), comment verbatim (`:178-184`):

> "The single respond produces: prompt -> tool call -> tool output -> response. By the time
> summarization's hook runs on the tool-output continuation, the history count (3) already exceeds the
> threshold (2), but the most recent entry is a tool output rather than a prompt. Because summarization
> only acts when the last entry is a prompt, it is skipped."

Result: the **entire history collapses to exactly ONE entry** — a single `.prompt` whose segments are
`[summary text] + original prompt segments`. Instructions, all prior prompts/responses/tool
exchanges: gone. `options` and `responseFormat` are carried over from the surviving prompt.

The default summarizer instructions verbatim (`SummarizeHistory.swift:112-129`):

```
Compress this conversation between an assistant and a user into a concise summary that preserves:
1. Established facts — names, numbers, dates, decisions, preferences.
2. The current topic and what stage the conversation is at.
3. The thread most recently raised by the user — often the immediate context for what comes next.
4. Any open questions or unresolved items.

Use compact third-person statements (for example: "User's dog is named Pepper, a border collie." or
"User is choosing between two apartments and has just decided office space is the deciding factor.").
Do not narrate the conversation with phrases like "the user said" or "they discussed". Compress
aggressively but do not drop the active conversational thread.
```

The default postamble verbatim (`SummarizeHistory.swift:76-83`):

```
Do not begin with phrases like "Based on the context", "Based on the facts", "Based on the summary",
or any reference to a summary or the facts provided. Treat the summary and facts above as things you
naturally remember.
```

Both are pinned by tests: default postamble at `SummarizeHistoryTests.swift:48-61`, custom at `:64-97`,
empty-string omission at `:99-129` (verifying that `""` suppresses both the postamble *and* its
blank-line separator).

### 6.6 `TranscriptRendering` — what it does

`Sources/FoundationModelsUtilities/History/TranscriptRendering.swift` (62 lines) is a purely
**internal** rendering helper (note `import FoundationModels` at `:12` — plain, not `public import`;
everything here is internal). Its only consumer is `SummarizeHistory.swift:134` (`history.chatLog()`).

```swift
extension Transcript.Entry {
  var chatText: String? {                                         // :18
    switch self {
    case .prompt(let prompt):        return "User: \(prompt.segments.textContent)"
    case .response(let response):    return "Assistant: \(response.segments.textContent)"
    case .reasoning(let reasoning):  return "Assistant (reasoning): \(reasoning.segments.textContent)"
    case .toolCalls(let calls):
      let rendered = calls.map { "\($0.toolName)(\($0.arguments))" }.joined(separator: ", ")
      return "Tool call: \(rendered)"                             // :31
    case .toolOutput(let output):
      return "Tool output (\(output.toolName)): \(output.segments.textContent)"   // :33
    case .instructions:              return nil                   // :35  ← dropped
    @unknown default:                return nil
    }
  }
}

extension Sequence where Element == Transcript.Entry {
  func chatLog(separator: String = "\n") -> String {              // :45
    compactMap(\.chatText).joined(separator: separator)
  }
}

extension Sequence where Element == Transcript.Segment {
  var textContent: String {                                       // :53
    compactMap { segment in
      if case .text(let textSegment) = segment { return textSegment.content }
      return nil
    }
    .joined(separator: " ")                                       // :60  ← SPACE separator
  }
}
```

Three facts worth carrying forward:
1. `.instructions` renders to `nil` and is **excluded** from the chat log — the summarizer never sees
   the system prompt.
2. `textContent` joins segments with a **space** (`:60`). The summarize tests deliberately avoid it,
   defining their own `promptText` with `joined()` and commenting: "Using `joined()` (no separator)
   avoids the space that `textContent` inserts between segments" (`SummarizeHistoryTests.swift:19-20`).
3. Structured content and attachments are **silently dropped** from the rendering.

`Transcript.ToolOutput` exposes a `toolName` (`:33`), and `Transcript.ToolCall` exposes `toolName` and
`arguments` (`:29`).

### 6.7 Modifier application order — "outside-in", resolved precisely

The README's composed example (`README.md:88-92`):

```swift
Profile {
  Instructions("A conversation between a user and a helpful assistant.")
  ToggleDarkModeTool()
}
.summarizeHistory(entryThreshold: 10, model: status.summarizerModel)
.rollingWindow(entries: 10)
.droppingCompletedToolCalls()
```

**Wrapping order (lexical):** `Profile` is wrapped by `summarizeHistory` first, that result by
`rollingWindow`, that result by `droppingCompletedToolCalls`. Therefore:

- `droppingCompletedToolCalls()` — **last written = OUTERMOST**
- `rollingWindow(entries: 10)` — middle
- `summarizeHistory(...)` — **first written = INNERMOST**

**Execution order at runtime:** outside-in, i.e. outermost first. So:
**drop tool calls → rolling window → summarize.**

Three independent source confirmations:

1. `README.md:78`: "Modifiers apply in outside-in order: first, the profile drops completed tool
   calls, then applies a rolling window."
2. `DropCompletedToolCalls.swift:23-25`: "applying it **outermost** ensures tool-call entries are
   cleaned up **before** a rolling window or summarization step runs" — followed by the exact same
   ordered example at `:30-33`.
3. `SummarizeHistory.swift:26-28`: "Because summarization is the most aggressive form of compression,
   it is typically placed **innermost** (applied last) so that lighter-weight modifiers like
   `droppingCompletedToolCalls()` and `rollingWindow(entries:)` **run first**."

The utilities skill restates the practical rule (`skills/foundation-models-utilities/SKILL.md:215`):
"the outermost call (`droppingCompletedToolCalls()` above) runs first, then the rolling window, then
summarization. Lighter compression first means heavier compression sees a smaller transcript."
And as a pitfall (`SKILL.md:295`): "**History modifiers run outside-in.** Apply summarization first in
source order so it ends up innermost; cheaper modifiers go last (they apply first at runtime)."

**Practical consequence for the README example** (both thresholds are 10): after
`droppingCompletedToolCalls()` prunes and `rollingWindow(entries: 10)` truncates to at most 10
entries, `summarizeHistory(entryThreshold: 10)` sees `history.count <= 10`, and its gate is
`history.count > entryThreshold` (strictly greater). **Summarization can therefore never fire in the
README's own example.** With equal numbers the composition is inert. To make it fire you need
`entryThreshold < rollingWindow entries` (e.g. the doc comments' `entryThreshold: 50` with
`rollingWindow(entries: 10)` is *also* inert — 10 is never > 50). In fact **every composed example
shipped in this repo is inert**: `DropCompletedToolCalls.swift:31-33`, `SummarizeHistory.swift:34-36`,
`skills/foundation-models-utilities/SKILL.md:210-212` and `:271-273` all pair
`entryThreshold: 50` with `rollingWindow(entries: 10 or 20)`. Flagged as a documentation defect
affecting all four call sites.

### 6.8 Where the README's "5000 tokens" comes from — RESOLVED

`README.md:78`:

> "Summarization runs only if the rolling window of 10 entries **exceeds 5000 tokens**."

**It is stale prose from a deleted, pre-beta-1 token-based API.** Evidence chain:

1. `grep -n "5000" README.md` → one hit, line 78 (prose only). `grep -rn "5000" Sources/ Tests/` → **zero hits**.
2. `git show 376ca60 -- README.md` shows the code sample was changed:

```diff
-    .summarizeHistory(threshold: 5000, model: summarizerModel)
+    .summarizeHistory(entryThreshold: 10, model: status.summarizerModel)
```

3. The **prose sentence on line 78 was never updated** to match.
4. `git show a047a50:Sources/…/SummarizeHistory.swift` confirms the source already used
   `entryThreshold: Int` compared against `history.count` at beta 1 — so the README's `threshold: 5000`
   sample **never compiled** against any shipped version of this package.

Verdict: **5000 is neither a parameter nor a default nor example-specific — it is a documentation
artifact of an abandoned token-threshold design.** The current API has no token awareness whatsoever.

Apple's own utilities skill flags it, though it mis-attributes the reason
(`skills/foundation-models-utilities/SKILL.md:249`):

> "Note: as of writing the `entryThreshold` parameter compares to entry count, not token count; the
> README example wording suggesting otherwise (e.g. 'exceeds 5000 tokens') is aspirational. **See the
> disabled / known-issue test in `SummarizeHistoryTests.swift`.**"

The referenced disabled test **does not exist** — `SummarizeHistoryTests.swift` has 5 tests, none
disabled, none tagged. (The only "documents the buggy outcome" test is in `RollingWindowTests.swift:60`.)

---

## 7. Platform & portability

### 7.1 Evidence inventory

| Evidence | Location | Reading |
|---|---|---|
| `.macOS("27.0") .iOS("27.0") .visionOS("27.0") .watchOS("27.0")` | `Package.swift:19-22` | Apple minimums; **no tvOS** |
| `#if canImport(FoundationNetworking) / public import FoundationNetworking` | `ChatCompletionsLanguageModel.swift:13-15` | non-Darwin (Linux/Windows) Foundation split module |
| `#if canImport(CoreImage) / private import CoreImage, UniformTypeIdentifiers` | `ChatCompletionsLanguageModel.swift:17-20` | Apple-only image encoding |
| `#if canImport(Darwin)` … `#else` in `streamChatCompletions` | `ChatCompletionsLanguageModel.swift:587` / `:605` | **two entirely different transport paths** |
| `#if canImport(CoreImage)` around image→JPEG conversion | `ChatCompletionsLanguageModel.swift:416` / `:422` | Apple-only vs URL-only image handling |
| `#if canImport(CoreImage) private extension CGImage { func jpegData() }` | `ChatCompletionsLanguageModel.swift:937-952` | Apple-only |
| `#if canImport(FoundationNetworking)` in tests | `ChatCompletionsTestUtilities.swift:13-15`, `MockSSE.swift:13-15`, `ChatCompletionsLiveTests.swift:13-15` | test harness is Linux-aware |
| `#if canImport(Darwin)` wrapping whole test suites | `ChatCompletionsTests+StructuredOutput.swift:12`, `+ToolCalling.swift:12`, `+Reasoning.swift:12` | **three suites are Apple-only** |
| **No CI config at all** | `find . -not -path "./.git/*"` — no `.github/`, no `.gitlab-ci.yml`, no `Dockerfile` | **no automated Linux verification exists** |
| `.spi.yaml` / `.spi.yml` | repo root | Swift Package Index docs config only; `documentation_targets: [FoundationModelsUtilities]`. No platform matrix. |

### 7.2 The three `#if canImport(Darwin)` test suites — why they're gated

- `ChatCompletionsTests+StructuredOutput.swift` — uses `@Generable struct MockWeatherInfo` and
  `session.respond(to:generating:)`.
- `ChatCompletionsTests+ToolCalling.swift` — uses `@Generable struct Arguments` inside a `Tool`.
- `ChatCompletionsTests+Reasoning.swift` — also declares a `@Generable` tool.

The common factor is the **`@Generable` macro**. The non-gated suites (`TextResponse`,
`UsageReporting`, `SSEEdgeCases`, `ErrorHandling`, `RequestFormat`, `Configuration`) use no
`@Generable`. Strong inference: **`@Generable` / guided generation is Darwin-only**, so structured
output and tool calling are effectively unavailable on Linux. **UNVERIFIED** as a framework-level
statement — inferred from which test files are gated, not from a framework declaration.

Note also: none of the **Skills** or **History** test files carry any platform guard, so those two
feature areas are presumptively portable (they use `Instructions`, `Prompt`, `Transcript`, `Mutex`,
`ObservationRegistrar` — nothing Darwin-specific). But `Skills.swift:269` builds a
`GenerationSchema` via `DynamicGenerationSchema`, which is the same guided-generation machinery, so
**Skills may in practice be Darwin-only too**. UNVERIFIED.

### 7.3 What is definitively Apple-only

1. **Incremental streaming.** `session.bytes(for:)` + `stream.lines` (`:588`, `:598`) is Darwin-only;
   Linux falls back to `session.data(for:)` (`:606`) which buffers the whole response. **Linux users
   get no token-by-token streaming** — `session.streamResponse` would deliver everything in one shot.
   This is the single most user-visible portability gap and it is not mentioned in the README.
2. **In-memory image attachments.** On Darwin, a `CGImage` is JPEG-encoded inline (`:418`). On Linux,
   an image attachment **must** carry a `url` or it throws `unsupportedTranscriptContent` (`:423-430`).
3. **`@Generable`-dependent features** (structured output, tool-argument schemas) — inferred, see §7.2.
4. `Bundle.main.bundleIdentifier` for `User-Agent` (`:224`) — always `nil` on a Linux server binary,
   so all Linux traffic identifies as `"com.apple.FoundationModels"`.

### 7.4 Assessment of the README's Linux claim

`README.md:10` — "💻 **Supported platforms**: Apple platforms and select Linux distributions like Ubuntu".

The claim is **structurally supported but unverified in practice**: the `#if canImport(FoundationNetworking)`
and `#if canImport(Darwin)` fallbacks are real and deliberate (and beta 3 *added* Linux-specific code —
the `guard let url = image.url` path at `:423`), but there is **no CI, no Dockerfile, no Linux job,
and no platform matrix anywhere in the repo**. Nothing in this repository proves the package compiles
on Linux. It requires a Linux `FoundationModels` module to exist, which is not evidenced here.

Relevant to session 241's "everywhere Swift runs, including Linux servers" pitch: this package is the
strongest *code-level* corroboration available, but with two large asterisks — no streaming, and
guided generation apparently gated.

---

## 8. The two agent skills (Apple's own written guidance)

Both live under `skills/` and are plain `SKILL.md` files with YAML frontmatter (`name`, `description`).
**Neither has a `references/` or `scripts/` subdirectory** — `find` confirms the only files under
`skills/` are the two `SKILL.md`s.

### 8.1 `skills/foundation-models-language-model-protocol/SKILL.md` (815 lines)

Frontmatter description (`:4`): triggered by "build a Foundation Models LanguageModel", "implement the
LanguageModel protocol", "wrap our inference API for Foundation Models", "create a server model
package for Apple", or work on `*LanguageModel.swift` / `*Executor.swift`.

**The protocol declarations, verbatim (`SKILL.md:42-58`) — the single most valuable artifact here:**

```swift
public protocol LanguageModel: Sendable {
  associatedtype Executor: LanguageModelExecutor where Executor.Model == Self
  var capabilities: LanguageModelCapabilities { get }
  var executorConfiguration: Executor.Configuration { get }
}

public protocol LanguageModelExecutor: Sendable {
  associatedtype Configuration: Hashable & Sendable
  associatedtype Model: LanguageModel
  init(configuration: Configuration) throws
  func respond(
    to request: LanguageModelExecutorGenerationRequest,
    model: Model,
    streamingInto channel: LanguageModelExecutorGenerationChannel
  ) async throws
  func prewarm(model: Model, transcript: Transcript)  // default no-op
}
```

**`LanguageModelExecutorGenerationRequest`, verbatim (`SKILL.md:265-273`):**

```swift
public struct LanguageModelExecutorGenerationRequest: Sendable {
  public var id: UUID
  public var transcript: Transcript
  public var enabledToolDefinitions: [Transcript.ToolDefinition]
  public var schema: GenerationSchema?
  public var generationOptions: GenerationOptions
  public var contextOptions: ContextOptions
  public var metadata: [String: any Sendable & Codable & Equatable]
}
```

`generationOptions` fields (`:282`): `temperature`, `samplingMode`, `maximumResponseTokens`,
`toolCallingMode`. `contextOptions` fields (`:283`): **`includeSchemaInPrompt`**, **`reasoningLevel`**
— described as "Prompting controls… Use `reasoningLevel` to set your provider's thinking-budget knob."
Neither is consumed by `ChatCompletionsLanguageModel`.

**The four capabilities (`SKILL.md:314-319`):** `.toolCalling`, `.vision`, `.reasoning`,
`.guidedGeneration` — `.guidedGeneration` defined as "Model **strictly** conforms output to a JSON
Schema", with the inline caution at `:110`: "include only if your model **strictly enforces** JSON Schema".

**The channel event API — three top-level cases (`SKILL.md:351`): `.response`, `.toolCalls`, `.reasoning`.**

Response actions (`:359-365`): `.appendText(_:segmentID:tokenCount:)`,
`.replaceTextSegment(_:segmentID:tokenCount:)`, `.updateCustomSegment(_:)`,
`.addAttachmentSegment(_:)`, `.removeAttachmentSegment(_:)`, `.updateMetadata(_:)`,
`.updateUsage(input:output:)`.

Reasoning actions (`:375-379`): `.appendText`, `.replaceTextSegment`, `.updateSignature(_:tokenCount:)`,
`.updateMetadata`, `.updateUsage`. **`entryID` is optional for reasoning** — "Pass `nil` to coalesce
into the trailing reasoning entry… Pass an explicit id when you need a stable anchor" (`:371`).

Tool-call outer actions (`:389-392`): `.toolCall(id:name:action:)`, `.removeToolCall(_:)`,
`.updateMetadata(_:)`, `.updateUsage(input:output:)`. Inner `ToolCall.Action` (`:398-399`):
`.appendArguments(_:tokenCount:)`, `.updateMetadata(_:)`.

**`Transcript.CustomSegment` — a protocol, not a type (`SKILL.md:408-415`):**

```swift
public protocol CustomSegment: Sendable, Identifiable, Equatable, CustomStringConvertible,
  PromptRepresentable, InstructionsRepresentable
{
  associatedtype Content: Sendable & Equatable & Codable
  var id: String { get }
  var content: Content { get }
}
```

Rationale at `:418`: "The framework uses `PromptRepresentable` / `InstructionsRepresentable` to know
how to fold the segment back into a future prompt when this entry becomes part of the transcript on a
subsequent turn."

**Attachment segments (`SKILL.md:455-463`):**

```swift
public struct AttachmentSegment: Sendable, Identifiable, Equatable {
  public var id: String
  public var content: Attachment
  public var label: String?
}

public enum Attachment: Sendable, Equatable {
  case image(ImageAttachment)
}
```

`ImageAttachment` buildable from "a `CGImage`, `CIImage`, `CVPixelBuffer`, or a `URL`" (`:483`).
There is **no `replaceAttachmentSegment`** — remove-then-add (`:494`).

**`Transcript.Entry` — the full enum (`SKILL.md:503-510`):**

```swift
public enum Entry {
  case instructions(Instructions)  // system prompt
  case prompt(Prompt)              // user message (may contain text + images)
  case toolCalls(ToolCalls)        // model's prior tool calls
  case toolOutput(ToolOutput)      // results returned from those tools
  case response(Response)          // model's prior text response
  case reasoning(Reasoning)        // model's prior reasoning
}
```

Six cases. Matches `EntrySummary.swift:36-52` and `TranscriptRendering.swift:19-38` exactly.

**`LanguageModelError` — all nine cases with payload fields (`SKILL.md:549-557`):**

| Case | Payload-specific fields |
|---|---|
| `.contextSizeExceeded(ContextSizeExceeded)` | `contextSize: Int`, `tokenCount: Int` |
| `.rateLimited(RateLimited)` | `resetDate: Date?` |
| `.guardrailViolation(GuardrailViolation)` | — |
| `.refusal(Refusal)` | `explanation: String` (required by the public initializer); surfaced via `refusal.explanation` / `refusal.explanationStream` |
| `.unsupportedCapability(UnsupportedCapability)` | `capability: LanguageModelCapabilities.Capability` |
| `.unsupportedTranscriptContent(UnsupportedTranscriptContent)` | `unsupportedContent: [Transcript.Entry]` |
| `.unsupportedGenerationGuide(UnsupportedGenerationGuide)` | `schemaName: String?` |
| `.unsupportedLanguageOrLocale(UnsupportedLanguageOrLocale)` | `languageCode: Locale.LanguageCode` |
| `.timeout(Timeout)` | — |

Plus (`:559`): "Every payload struct exposes `debugDescription: String` … and
`metadata: [String: any Sendable]`". Construction examples at `:561-613`.

**The ten pitfalls, verbatim headlines (`SKILL.md:804-814`):**

1. `updateUsage` is wholesale, not additive.
2. `updateMetadata` are wholesale snapshots — "A subsequent event with fewer items REMOVES the missing ones."
3. Every `.toolCall(id:name:action:)` event must carry the function `name` — not just the opener.
4. Emit per-call metadata BEFORE the first `.appendArguments` for that id.
5. Use `.removeToolCall(_:)` when the model retracts a streamed tool call — "there is no `replaceArguments` equivalent."
6. Attachments add, they don't replace.
7. Don't try to "fix up" prior text via mutation — use `replaceTextSegment`.
8. Reasoning signatures are opaque bytes — "Don't UTF-8 decode them assuming text."
9. Pick an `entryID` strategy for reasoning and stick to it.
10. Don't declare a capability you don't fully support.
11. Configuration must hold only Hashable primitives.

Also: auth patterns (OAuth vs API key, `:321-347`), cancellation (`:637-648` — "When cancelled, return
or throw `CancellationError()`. The framework manages the channel lifetime around your `respond(...)`
call"), package layout (`:659-708`), and a three-layer testing strategy (`:712-800`) — request-builder
unit tests, event-translator unit tests with a recording sink, and end-to-end through
`LanguageModelSession`. A notable testing caveat (`:766-768`): "Inspect the recorded event by matching
on `kind.storage` to recover the typed `Response` / `Reasoning` / `ToolCalls` payload… **(Channel events
are not Equatable, so a literal `==` against an event literal won't compile.)**"

The skill also uses Swift's **backtick-quoted test names** throughout (e.g.
``@Test func `system instructions become a system message`()``), matching the real test files.

#### What changed in this skill at beta 3 (`git show 376ca60 -- skills/`)

- `LanguageModelCapabilities(capabilities: [...])` → `LanguageModelCapabilities([...])`.
- `.removeToolCall(id:)` → **`.removeToolCall(_:)`** taking a `Transcript.ToolCall`.
- `.removeAttachmentSegment(id:)` → **`.removeAttachmentSegment(_:)`** taking an `AttachmentSegment`.
- **New section "Inspecting option types"** introducing the `.kind` projection — "Several framework
  option types are enum-like structs you can *construct* but historically couldn't *read*. To let
  executors translate them, there is now a `kind` property on each." Plus the note that
  `GenerationSchema` "conforms to `Codable` and encodes to standard JSON Schema".
- `.refusal(Refusal)` gained a **required** `explanation: String`, and the example
  `LanguageModelError.Refusal(debugDescription:)` throw was **deleted** (it no longer compiles).

### 8.2 `skills/foundation-models-utilities/SKILL.md` (327 lines)

**This file was NOT touched in commit `376ca60`** (`git show 376ca60 --stat` lists only
`skills/foundation-models-language-model-protocol/SKILL.md`). It therefore describes beta 1 and is
**stale in seven verifiable places**:

| # | SKILL.md claim | Line | Reality at HEAD |
|---|---|---|---|
| 1 | "Three independent feature areas, each guarded by its own SwiftPM trait" — `ChatCompletions`, `Skills`, `History`; "source files are gated by `#if ChatCompletions`, `#if Skills`, and `#if History`" | :9-17, :326 | **No traits in `Package.swift`. Zero `#if ChatCompletions/Skills/History` in any source file.** Entirely fictional. |
| 2 | `SkillActivations` "conforms to `RandomAccessCollection<String>`", with `ForEach(assistant.activations, id: \.self)` | :150, :158 | Removed in beta 3. Use `.activeSkillNames`. The snippet won't compile. |
| 3 | `summarizeHistory(entryThreshold:model:…)` with `model: Model = SystemLanguageModel()` | :234, :243 | **No default for `model:`** (`SummarizeHistory.swift:55`). |
| 4 | Initializer shown without `urlSessionConfiguration` | :46-52 | Added in beta 3 (`ChatCompletionsLanguageModel.swift:78`). |
| 5 | Toggle-tool descriptions are `"Activate or deactivate a skill"` / `"Activates a skill"` | :170 | Replaced in beta 3 by the long "…Don't ask the user for permission…" forms (`Skills.swift:259-266`), test-pinned at `SkillsTests.swift:139-202`. |
| 6 | `response_format` name "is read from the schema's `title`/`type`, falling back to `"Response"`" | :72 | The `GenerationSchema.title` hack was **deleted** in beta 3; now `schema.name` (`ChatCompletionsLanguageModel.swift:266`). |
| 7 | Package layout shows `Tests/FoundationModelsUtilitiesEvaluations/  # eval-driven tests for summarization` | :323 | Directory doesn't exist. Actual second target is `FoundationModelsUtilitiesIntegrationTests`. |
| 8 | "See the disabled / known-issue test in `SummarizeHistoryTests.swift`" | :249 | No such test. |

It also **omits** the `Skills(instructions:)` parameter and the default leading instruction, both new
in beta 3.

**Where it is still correct and uniquely useful:**

- The two-flavor `Skill` table with the KV-cache column (`:141-144`) — matches source exactly.
- The choose-which guidance (`:146`): "Choose prompt-based when the body is large or only relevant for
  one turn (style guides, reference docs, big rules). Choose instructions-based when the body is short,
  must take effect across many turns, and benefits from being treated as system-level instructions."
- The wire-format summary (`:69-76`) and SSE-parsing summary (`:80-87`).
- The pitfalls list (`:289-298`), of which these are verified-correct and quotable:
  - "**Base URL handling is 'include `/v1` or don't'.**" (§4 — understated but accurate)
  - "**A `Skills` activation produces a tool call in the transcript.** Even prompt-based skills generate
    a tool-call/tool-output pair."
  - "**`SkillActivations` is a reference type and `Sendable`.** Hold one per 'session-equivalent'…
    Don't recreate it on every render or you'll lose the activation state and break observation."
  - "**`summarizeHistory` requires the trailing entry to be `.prompt`.** It is a no-op for any other
    trailing entry kind."
  - "**Custom segments aren't supported by `ChatCompletionsLanguageModel`.**"
- The full composed example (`:255-285`) showing `LanguageModelSession(profile: AgentProfile(…).model(model))`.

---

## 9. Framework API surface incidentally revealed by this package

Symbols used here that are defined in `FoundationModels`, not in this repo. Grouped by confidence.

**Directly exercised in compiled source or tests (high confidence):**

`LanguageModel`, `LanguageModelExecutor`, `LanguageModelCapabilities` (+ `.vision`, `.toolCalling`,
`.reasoning`, `.guidedGeneration`; both `init(_:)` and `init(capabilities:)`; `.contains(_:)`),
`LanguageModelExecutorGenerationRequest`, `LanguageModelExecutorGenerationChannel` (+ `.send(_:)`),
`LanguageModelError` (+ `.unsupportedTranscriptContent`, `.UnsupportedTranscriptContent(unsupportedContent:debugDescription:)`),
`LanguageModelSession` (+ `init(model:)`, `init(model:instructions:)`, `init(model:tools:)`,
`init(profile:)`, `.respond(to:)`, `.respond(to:generating:)`, `.transcript`),
`LanguageModelSession.Profile`, `LanguageModelSession.DynamicProfile`,
`LanguageModelSession.DynamicProfileModifier` (+ `Content`, `body(content:)`, `.modifier(_:)`),
`DynamicProfile.onPrompt { }`, **`DynamicProfile.model(_:)`** (moved into the framework at beta 3),
`@SessionProperty(\.history)`, `DynamicInstructions`, `DynamicInstructions.ForEach(_:id:_:)`,
`AnyDynamicInstructions`, `@DynamicInstructionsBuilder`, `Instructions`, `InstructionsRepresentable`,
`Prompt`, `@PromptBuilder`, `Tool` (+ `name`, `description`, `parameters`, `call(arguments:)`),
`@Generable`, `GenerationSchema` (+ `.name`, `Codable`), `DynamicGenerationSchema`
(+ `init(name:properties:)`, `init(type:guides:)`, `.Property(name:schema:)`, `.anyOf(_:)`),
`GeneratedContent` (+ `.value(_:forProperty:)`, `.jsonString`, `.ParsingError(rawContent:debugDescription:)`),
`GenerationOptions` (+ `.temperature`, `.samplingMode`, `.maximumResponseTokens`, `.toolCallingMode`,
`.SamplingMode.kind` → `.greedy` / `.randomTopK` / `.randomProbabilityThreshold(_:_:)`,
`.toolCallingMode?.kind` → `.allowed` / `.required` / `.disallowed`),
`Transcript` (+ `Entry`, `Segment`, `TextSegment(content:)`, `Prompt(id:segments:options:responseFormat:)`,
`Instructions`, `Response`, `Reasoning`, `ToolCalls`, `ToolCall(id/toolName/arguments)`,
`ToolOutput(id/toolName/segments)`, `ToolDefinition(name/description/parameters)`),
`Response.usage` (+ `.input.totalTokenCount`, `.input.cachedTokenCount`, `.output.totalTokenCount`,
`.output.reasoningTokenCount`).

**Documented in SKILL.md only (medium confidence — Apple's prose, no compiled use here):**

`ContextOptions` (`includeSchemaInPrompt`, `reasoningLevel`), `Transcript.CustomSegment`,
`Transcript.AttachmentSegment`, `Transcript.Attachment`, `Transcript.ImageAttachment`,
`Transcript.ResponseFormat.kind`, `PromptRepresentable`, `SystemLanguageModel`,
the six remaining `LanguageModelError` cases, `.updateSignature`, `.replaceTextSegment`,
`.updateCustomSegment`, `.addAttachmentSegment`, `.removeAttachmentSegment`, `.removeToolCall`,
`.updateMetadata`, `prewarm(model:transcript:)`, `refusal.explanationStream`,
`LanguageModelCapabilities.Capability`.

**Mentioned once, nowhere else (low confidence):** `session.logFeedbackAttachment` (`CONTRIBUTING.md`).

**Deleted-but-instructive:** `git show a047a50:…/DynamicProfile+LanguageModel.swift` contains a
complete hand-rolled **`AnyLanguageModel` type-eraser** (92 lines), removed at beta 3 because the
framework now ships `.model(any LanguageModel)`. It is the best available illustration of how the
associated-type dance is erased:

```swift
var executorConfiguration: Executor.Configuration {
  func projectExecutorType<L: LanguageModel>(_ model: L) -> L.Executor.Type { L.Executor.self }
  return Executor.Configuration(storage.executorConfiguration, executorType: projectExecutorType(storage))
}
…
struct Configuration: Hashable, Equatable, @unchecked Sendable {
  fileprivate let configuration: AnyHashable
  fileprivate let executorType: Metatype
}
private struct Metatype: Hashable, Equatable, @unchecked Sendable {
  private let type: UnsafeRawPointer
  init(_ swiftType: Any.Type) { type = unsafeBitCast(swiftType, to: UnsafeRawPointer.self) }
  var swiftType: Any.Type { unsafeBitCast(type, to: (Any.Type).self) }
}
```

Note the `unsafeBitCast` of a metatype to `UnsafeRawPointer` purely to obtain `Hashable` — evidence of
how load-bearing `Configuration: Hashable` is to the executor cache.

---

## 10. Bugs, defects, and doc/source divergences found (consolidated)

**Source bugs / fragilities**

1. **`buildURLRequest` version detection** — `ChatCompletionsLanguageModel.swift:635-637`. Confirmed,
   empirically reproduced, never fixed, no escape hatch. §4.
2. **`rollingWindow` splits prompt/response pairs** — `RollingWindow.swift:79`. Apple's own test comment:
   "documents the (buggy) naive outcome; in practice it crashes partway through"
   (`RollingWindowTests.swift:71-73`).
3. **`Executor.Configuration` excludes `urlSession` from `==`/`hash`** — `ChatCompletionsLanguageModel.swift:201-211`.
   Two models differing only in `urlSessionConfiguration` are cache-equal, so the framework may reuse an
   executor built with the wrong session. Latent.
4. **SSE parser requires exactly `"data: "` with one space** — `:658`. `data:{...}` (spec-legal) is
   silently dropped. Untested.
5. **Tool-call id/name latching uses `+` not `??`** — `:314-315`. A server that repeats the full id on
   every delta produces a concatenated id.
6. **Tool-call deltas suppress same-chunk text** — the `else if` at `:335`. A chunk with both
   `tool_calls` and `content` loses the `content`.
7. **No `Task.checkCancellation()` in the stream loop** — contradicts the skill's own instruction at
   `SKILL.md:637-648`. Only `onTermination` → `task.cancel()` at `:630`.
8. **`response as! HTTPURLResponse`** force casts at `:589` and `:607`; `try!` on `GenerationSchema`
   at `Skills.swift:269`; `!` on `CGImageDestinationCreateWithData` at `:946`.
9. **No typed `LanguageModelError` mapping for HTTP status codes** — a 429 becomes a generic
   `RequestError.httpError`, never `.rateLimited`, despite the skill instructing third parties otherwise.

**Documentation defects**

10. **README "5000 tokens"** (`README.md:78`) — stale prose from a removed token-threshold API. §6.8.
11. **README malformed URL** `http://localhost/v1:8000` at `README.md:52` and `:67`. §4.
12. **README `RandomAccessCollection` claim** (`README.md:100`) — removed at beta 3. §5.5.
13. **README `from: "1.0.0"`** (`README.md:30`) — no non-prerelease tag exists; resolves to nothing. §2.
14. **All four composed history examples are inert** — `entryThreshold` ≥ window size in
    `README.md:89-90`, `DropCompletedToolCalls.swift:31-32`, `SummarizeHistory.swift:34-35`,
    `skills/foundation-models-utilities/SKILL.md:210-211` and `:271-272`. §6.7.
15. **`skills/foundation-models-utilities/SKILL.md` is a beta-1 document** — eight verified stale
    claims including entirely fictional SwiftPM traits. §8.2.
16. **Linux support asserted with zero CI** — no `.github/`, no Dockerfile, no build matrix. §7.4.

---

## 11. Source inventory — every file read this session

**Read in full:**

| Path | Lines | Notes |
|---|---|---|
| `README.md` | 235 | incl. all 3 ASCII diagrams (reproduced §12) |
| `Package.swift` | 65 | |
| `CONTRIBUTING.md` | — | |
| `.gitignore`, `.spi.yaml`, `.spi.yml`, `.swift-format` | — | |
| `Sources/FoundationModelsUtilities/Documentation.docc/Documentation.md` | 34 | |
| `Sources/FoundationModelsUtilities/LanguageModels/ChatCompletionsLanguageModel.swift` | 953 | |
| `Sources/FoundationModelsUtilities/History/DropCompletedToolCalls.swift` | 68 | |
| `Sources/FoundationModelsUtilities/History/RollingWindow.swift` | 90 | |
| `Sources/FoundationModelsUtilities/History/SummarizeHistory.swift` | 165 | |
| `Sources/FoundationModelsUtilities/History/TranscriptRendering.swift` | 62 | |
| `Sources/FoundationModelsUtilities/Skills/Skill.swift` | 247 | |
| `Sources/FoundationModelsUtilities/Skills/Skills.swift` | 321 | |
| `Sources/FoundationModelsUtilities/Skills/SkillActivations.swift` | 56 | |
| `Sources/FoundationModelsUtilities/Skills/SkillBuilder.swift` | 75 | |
| `skills/foundation-models-language-model-protocol/SKILL.md` | 815 | |
| `skills/foundation-models-utilities/SKILL.md` | 327 | |
| `Tests/FoundationModelsUtilitiesTests/MockModel.swift` | 122 | |
| `Tests/FoundationModelsUtilitiesTests/EntrySummary.swift` | 64 | |
| `Tests/FoundationModelsUtilitiesTests/TestUtilities.swift` | 39 | |
| `Tests/…/SkillsTests/SkillsTests.swift` | 679 | |
| `Tests/…/SkillsTests/SkillTests.swift` | 105 | |
| `Tests/…/SkillsTests/SkillBuilderTests.swift` | 203 | |
| `Tests/…/HistoryTests/SummarizeHistoryTests.swift` | 190 | |
| `Tests/…/HistoryTests/DroppingCompletedToolCallsTests.swift` | 80 | |
| `Tests/…/HistoryTests/RollingWindowTests.swift` | 93 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTests.swift` | 15 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTestUtilities.swift` | 57 | |
| `Tests/…/LanguageModelTests/MockSSE.swift` | 227 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+RequestFormat.swift` | 86 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+Configuration.swift` | 56 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+ErrorHandling.swift` | 43 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+TextResponse.swift` | 46 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+StructuredOutput.swift` | 100 | `#if canImport(Darwin)` |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+ToolCalling.swift` | 135 | `#if canImport(Darwin)` |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+Reasoning.swift` | 174 | `#if canImport(Darwin)` |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+SSEEdgeCases.swift` | 104 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+UsageReporting.swift` | 165 | |
| `Tests/…/LanguageModelTests/ChatCompletionsTests+Live.swift` | 83 | env-gated |
| `Tests/FoundationModelsUtilitiesIntegrationTests/ChatCompletionsLiveTests.swift` | 61 | env-gated |

**Not read (binary):** `assets/fm-icon-27.png`, `LICENSE.txt` (standard Apache 2.0, verified via `gh`).

**Git artifacts examined:** `git log --oneline -50`; `git log --stat -5`; `git show 376ca60` (full,
plus scoped to `README.md`, `Sources/…/ChatCompletionsLanguageModel.swift`, `skills/`);
`git show a047a50:Sources/…/SummarizeHistory.swift`;
`git show a047a50:Sources/…/LanguageModels/DynamicProfile+LanguageModel.swift` (deleted file);
`git log -p --all -S "pathComponents.contains"`; `git tag -l`; `git ls-remote`.

**GitHub queries:** `gh issue list --state all --limit 50` (issues disabled);
`gh pr list --state all --limit 50` (empty); `gh release list` (empty); `gh repo view --json …`.

**Executed:** a standalone Swift script reproducing `buildURLRequest`'s two decisive lines against
Swift 6.3.3 Foundation, over 11 base-URL shapes (§4 table).

**Environment note:** the local toolchain is Swift 6.3.3 / `arm64-apple-macosx26.0`. The package
requires macOS **27.0** and a `FoundationModels` module providing `LanguageModel`. **The package could
not be compiled or its tests run in this session.** All behavioral claims are from source reading plus
Apple's own test assertions, except the URL logic, which was executed in isolation.

---

## 12. README ASCII diagrams (verbatim)

### 12.1 Prompt-based skill activation — content lands in TOOL OUTPUT (KV cache preserved)
`README.md:154-170`

```
         Before                         After
┌───────────────────────┐      ┌───────────────────────┐
│     Instructions      │      │     Instructions      │
│      (original)       │      │      (original)       │
├───────────────────────┤      ├───────────────────────┤
│        Prompt         │      │        Prompt         │
└───────────────────────┘      ├───────────────────────┤
                               │      Tool Call        │
                               │  (activate: skill_a)  │
                               ├───────────────────────┤
                               │     Tool Output       │
                               │   (skill_a content)   │
                               ├───────────────────────┤
                               │       Response        │
                               └───────────────────────┘
```

### 12.2 Instructions-based skill activation — content merged into INSTRUCTIONS (KV cache invalidated)
`README.md:174-190`

```
            Before                                  After
┌────────────────────────────────┐      ┌────────────────────────────────┐
│          Instructions          │      │          Instructions          │
│           (original)           │      │  (original + skill_a content)  │
├────────────────────────────────┤      ├────────────────────────────────┤
│             Prompt             │      │             Prompt             │
└────────────────────────────────┘      ├────────────────────────────────┤
                                        │           Tool Call            │
                                        │       (activate: skill_a)      │
                                        ├────────────────────────────────┤
                                        │           Tool Output          │
                                        │    (skill activated message)   │
                                        ├────────────────────────────────┤
                                        │            Response            │
                                        └────────────────────────────────┘
```

### 12.3 Deactivation + `droppingCompletedToolCalls()` — full context reclamation
`README.md:208-234`

```
            Before                                  After                 Dropping Completed Tool Calls
┌────────────────────────────────┐  ┌────────────────────────────────┐  ┌────────────────────────────────┐
│          Instructions          │  │          Instructions          │  │          Instructions          │
│  (original + skill_a content)  │  │           (original)           │  │           (original)           │
├────────────────────────────────┤  ├────────────────────────────────┤  ├────────────────────────────────┤
│             Prompt             │  │             Prompt             │  │             Prompt             │
├────────────────────────────────┤  ├────────────────────────────────┤  ├────────────────────────────────┤
│           Tool Call            │  │           Tool Call            │  │            Response            │
│       (activate: skill_a)      │  │       (activate: skill_a)      │  ├────────────────────────────────┤
├────────────────────────────────┤  ├────────────────────────────────┤  │             Prompt             │
│           Tool Output          │  │           Tool Output          │  ├────────────────────────────────┤
│    (skill activated message)   │  │    (skill activated message)   │  │            Response            │
├────────────────────────────────┤  ├────────────────────────────────┤  └────────────────────────────────┘
│            Response            │  │            Response            │
└────────────────────────────────┘  ├────────────────────────────────┤
                                    │             Prompt             │
                                    ├────────────────────────────────┤
                                    │           Tool Call            │
                                    │     (deactivate: skill_a)      │
                                    ├────────────────────────────────┤
                                    │           Tool Output          │
                                    │  (skill deactivated message)   │
                                    ├────────────────────────────────┤
                                    │            Response            │
                                    └────────────────────────────────┘
```

The third diagram is the package's thesis: **skills + deactivation + `droppingCompletedToolCalls()`
compose into a complete context-reclamation loop**, returning the transcript to a clean
prompt/response alternation with the instructions entry restored to its original bytes. This is what
`skills/foundation-models-utilities/SKILL.md:146` means by "useful in combination with
`droppingCompletedToolCalls()` to fully evict the activation/deactivation tool-call pair from history."

---

## 13. `Documentation.docc/Documentation.md` — the DocC landing page

Full symbol-link inventory (this is the package's own curated API index):

```
### Language Models
- ``ChatCompletionsLanguageModel``

### Skills
- ``Skill``
- ``Skills``
- ``SkillActivations``
- ``SkillsBuilder``

### Context Management
- ``FoundationModels/LanguageModelSession/DynamicProfile/summarizeHistory(entryThreshold:model:instructions:summaryPostamble:)``
- ``FoundationModels/LanguageModelSession/DynamicProfile/rollingWindow(entries:)``
- ``FoundationModels/LanguageModelSession/DynamicProfile/rollingWindow(size:)``
- ``RollingWindowSize``
- ``FoundationModels/LanguageModelSession/DynamicProfile/droppingCompletedToolCalls()``
```

**Nine public symbols total.** This is the complete public API surface of the package. Note
`TranscriptRendering`'s `chatLog()` / `chatText` / `textContent` are absent — they are internal.
The DocC file is the only doc source that is fully accurate at HEAD, and it confirms
`summarizeHistory`'s exact four-parameter selector.

It also carries one prose claim worth quoting for guides:

> "**Skills.** `Skills` and `Skill` teach a session about specialized tasks just-in-time. The model
> activates a skill by issuing a tool call, and the corresponding prompt or instructions content is
> added to the transcript only when needed — keeping the upfront context small and **protecting the
> key-value cache**."

---

## 14. Open questions / UNVERIFIED

1. **Does `FoundationModels` actually exist on Linux?** The package is structured for it
   (`FoundationNetworking`, non-Darwin branches, beta-3 additions to the Linux image path), but nothing
   in this repo — no CI, no Dockerfile, no build log — proves it compiles there. The README claim
   (`README.md:10`) is unbacked by any artifact in the repository.
2. **Is `@Generable` Darwin-only?** Inferred from the fact that exactly the three test suites using
   `@Generable` carry `#if canImport(Darwin)`. Not stated anywhere as a framework fact.
3. **Are Skills usable on Linux?** `Skills.swift:269` builds a `GenerationSchema` from a
   `DynamicGenerationSchema` — the same guided-generation machinery. If (2) holds, Skills is Darwin-only
   in practice despite having no platform guard. Unresolved.
4. **`@SessionProperty` semantics.** Its full API (other key paths besides `\.history`, whether writes
   are transactional, ordering vs. other modifiers) is unknown; only `\.history` read/write is used here.
5. **`.onPrompt { }` ordering guarantee.** "Outside-in" is asserted in three doc comments and the README
   but never *demonstrated* by a test composing two modifiers. All three history test files apply exactly
   one modifier. **The composition order claim is documented but not test-verified anywhere in the repo.**
6. **Why does `.instructions` survive `rollingWindow(entries: 2)`?** `RollingWindowTests.swift:74-80`
   expects `.instructions` at index 0 even though `suffix(2)` should drop it. The framework must
   re-materialize the instructions entry after modifiers run. Mechanism unknown.
7. **`AnyDynamicInstructions`** — used at `Skill.swift:183`, `:223`, `:235`. Public or internal
   framework API? Its initializer accepts `some DynamicInstructions`. Not defined in this repo.
8. **`GenerationSchema.name`** — new at beta 3. What does it return for an anonymous / inline schema?
   The deleted `title` extension had a `"Response"` fallback; whether `.name` has an equivalent is unknown.
9. **`session.logFeedbackAttachment`** — named once in `CONTRIBUTING.md`, defined nowhere here.
   Property or method? Return type?
10. **`ContextOptions.reasoningLevel`** — the type of the "thinking-budget knob" (enum? Int?) is not
    shown. Described only in prose at `SKILL.md:283`.
11. **`Transcript.ImageAttachment.url` optionality** — inferred Optional at beta 3 from the diff
    (`guard let url = image.url`). Not directly confirmed against a framework declaration.
12. **Does `Executor.Configuration` ignoring `urlSession` actually cause executor mis-reuse?** Depends
    on framework cache semantics (lifetime, eviction). Reasoned from `SKILL.md:65` + the manual
    `Hashable`, not observed.
13. **`repository pushedAt` 2026-07-16 vs. HEAD commit 2026-07-10.** A six-day gap with no new commit
    on `main` and no new tags. Possibly a branch deletion, a settings change, or a force-push. The
    clone may be one push behind. Unresolved.
14. **No `tvOS` in `Package.swift:18-23`.** Deliberate exclusion or oversight? Unknown.
15. **Framework `.model(any LanguageModel)`** — moved into `FoundationModels` at beta 3. Whether the
    framework's version uses the same `Metatype`/`unsafeBitCast` approach as the deleted
    `AnyLanguageModel` is unknown.

---

## 15. Guide topics this material supports

1. **"Implementing the `LanguageModel` protocol: a complete walkthrough."** The protocol declarations
   (`SKILL.md:42-58`), `LanguageModelExecutorGenerationRequest` (`:265-273`), and a full 953-line worked
   conformance. The only readable source for this API anywhere in the corpus.
2. **"The executor channel event API."** All three top-level events, every action, `entryID` hygiene,
   the coalescing rule (only *consecutive* same-type events merge), `updateUsage`/`updateMetadata`
   wholesale-replacement semantics, and the eleven pitfalls — with a real streaming implementation
   (`processChunks`, `:280-365`) demonstrating each.
3. **"`LanguageModelError`: all nine cases, and when to throw each."** Complete table with payload
   fields, construction examples, plus a case study in what happens when you *don't* map them
   (ChatCompletions' generic `httpError` for 429).
4. **"Skills: just-in-time context injection and the KV-cache tradeoff."** Prompt-vs-instructions
   confirmed in source, three rendering states, the synthesized tool, `strictSchema`, the
   activate/toggle naming rule, four test-pinned default descriptions, and the builder-with-tools
   initializer that gates a whole toolset behind an activation.
5. **"Context-window management with `DynamicProfile` modifiers."** Three exact signatures, the
   outside-in order semantics resolved precisely, the `@SessionProperty(\.history)` + `.onPrompt`
   pattern for writing your own, and the inert-composition trap (all four shipped examples).
6. **"Connecting Foundation Models to OpenAI-compatible endpoints."** Complete wire mapping in both
   directions, SSE parsing, reasoning round-trip, usage reporting — plus the URL-versioning bug and
   its `/api/v1` workaround, which is essential practical knowledge for Ollama / vLLM / LM Studio /
   Gemini-compat / Azure users.
7. **"Foundation Models beyond Apple platforms."** The `FoundationNetworking` / `canImport(Darwin)`
   evidence, the no-streaming-on-Linux finding, the Darwin-gated test suites, and the honest
   assessment that no CI verifies any of it — directly relevant to session 241's "everywhere Swift
   runs" pitch.
8. **"Executor caching and the `Configuration` contract."** Why `Hashable` is load-bearing, what
   belongs in a Configuration, the manual conformance workaround for `URLSession`, and the deleted
   `AnyLanguageModel` type-eraser as an illustration of the associated-type machinery.
9. **"Testing a custom `LanguageModel`."** The three-layer strategy from Apple's skill, plus two
   complete working mocks (`MockModel` with a turn-indexing event machine; `SkillsMockModel`), a
   `URLProtocol`-based SSE fixture generator (`MockSSE.swift`, 227 lines), transcript-summary
   assertion helpers (`EntrySummary.swift`), and the env-gated live-integration pattern.
10. **"Transcript anatomy."** All six `Entry` cases, the segment kinds (text / structure / attachment /
    custom), role mapping to chat-completions, reasoning buffering-and-attachment, and plain-text
    rendering for downstream summarization (`TranscriptRendering.swift`).
11. **"What changed between Xcode 27 beta 1 and beta 3."** A rare, precisely dated API-delta record:
    `SamplingMode` renames, `LanguageModelCapabilities` initializer, `GenerationSchema.name` replacing
    a JSON-title hack, `.removeToolCall`/`.removeAttachmentSegment` value-taking forms, the `.kind`
    readable projections, `Refusal.explanation` becoming required, `ImageAttachment.url` becoming
    Optional, and `.model(_:)` graduating into the framework.
