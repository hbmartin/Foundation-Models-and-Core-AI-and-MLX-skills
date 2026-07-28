# FM Ecosystem — transcript deep-read notes

**Theme:** the expansion of the Foundation Models framework beyond the on-device system model —
Private Cloud Compute server LLM, the public model-provider protocol (any local/server LLM),
the four model options, image input, and Core Spotlight integration.

**Agent scope:** deep-read of three WWDC26 transcripts, in full, plus cross-check against the
local `docs/`, `repos/`, and `forums/` corpora in this project.

**Transcripts read (verbatim, full):**

| File | Session | Presenter | Lines |
|---|---|---|---|
| `transcripts/wwdc2026-319.txt` | "Build with the new Apple Foundation Model on Private Cloud Compute" (title inferred from cross-refs) | **Louis** | 109 |
| `transcripts/wwdc2026-339.txt` | "Bring an LLM provider to the Foundation Models framework" (title confirmed by `repos/john-rocky__coreai-model-zoo/knowledge/fm-provider.md:9` and forums thread 836264) | **Christopher Webb**, Machine Learning Research team | 213 |
| `transcripts/wwdc2026-246.txt` | "LLM search using Core Spotlight" (title from `repos/john-rocky__coreai-model-zoo/knowledge/spotlight-rag-third-party.md:3`) | **Jennifer**, Spotlight engineering team | 138 |

> **PROVENANCE RULE FOR THIS FILE.** Everything attributed to a transcript is quoted or
> paraphrased from the line numbers cited. Code shown on screen but only *described* aloud is
> marked **[RECONSTRUCTED]** and, where possible, corroborated against a written source in the
> local corpus. Anything I could not corroborate is marked **UNVERIFIED**.

---

## 0. The one-paragraph shape of the year

Session 339 line 6 is the thesis of the whole theme:

> "The on-device System Language Model has been rebuilt from the ground up: it's smarter, better
> at instruction following, and accepts images directly in your prompts. **Beyond the system
> model, we've added three more options.**"

The four model options, in Apple's own ordering (339:5–9):

1. **`SystemLanguageModel`** — on-device, rebuilt, now accepts images directly in prompts.
2. **Private Cloud Compute** — "the model behind many Apple Intelligence features: now with
   reasoning, a 32K token context window, and the privacy guarantees you'd expect."
3. **Core AI** — "lets you run local models efficiently and take advantage of the ANE."
4. **MLX** — "unlocks the thousands of models available via the MLX-Community on Hugging Face."

…plus an open fifth category: anything conforming to the new public `LanguageModel` protocol.

> 339:10–12 — "And because these are built on top of a brand new **public protocol**, developers
> can bring frontier AI models into their apps using the same framework. **Anthropic and Google
> will soon extend the Foundation Models framework with Swift packages of their own, making
> state-of-the-art Claude and Gemini models available to all Swift developers.** Which ever model
> you use, Apple's, yours, or the community's, you call them the same way, because every model
> conforms to the Language Model protocol."

And the sleeper announcement, 339:42:

> "And because the **Foundation Models framework is being released as open source**, your package
> could also be useful to developers who deploy Swift on their servers, so consider supporting
> **Linux** too."

---

# PART A — WWDC26-319: Private Cloud Compute server LLM

Presenter: Louis. 109 lines. Shortest of the three; densest on product/policy facts.

## A.1 What was announced

- Line 3–5: last year gave the on-device LLM; **this year the on-device LLM is improved**:
  "It now has support for **image input**, it's **better at instruction following** and **calling
  your custom tools**."
- Line 6–7: "But we know there are more complex use cases that require an even more powerful
  model. So this year we're also giving you access to a **new server model running on Private
  Cloud Compute**."
- Line 8–9 — the target use cases, verbatim:
  > "you can build complex AI features in your apps. Like **assistants that reason over large user
  > input** or **features that rely on making lots of tool calls, with large outputs**, And you can
  > even **call Private Cloud Compute from watchOS**."

**watchOS PCC is explicit.** Corroborated in `forums/machine-learning-and-ai-foundation-models.txt:190-200`
(thread 834652, "Can any Apple Watch running WatchOS 27 access PCC via Foundation Models?"):
"it says that Foundation Models PCC calls are supported on all Apple Watch models that run
WatchOS 27." The forum poster raises an unanswered question about the Apple Intelligence
setting on watchOS when paired with a non-AI-capable iPhone → see Open Questions.

## A.2 The privacy / auth / cost pitch (319:12–27)

Verbatim, sequential:

- 12: "Private Cloud Compute powers our system features, to send complex tasks to Apple's servers.
  And you now get access to this in your apps as well."
- 14: "you can access a powerful server LLM, **without compromising on privacy**."
- 15–17: "Private Cloud Compute is designed with **end-to-end privacy** in mind, ensuring that
  **user data is never stored**. The data is only used for requests. And all of this has been
  **independently verified by researchers**."
- 19–22: "Private Cloud Compute is integrated in the OS, together with **iCloud**. So you **don't
  have to worry about authentication or API keys**, like you typically do with server models. Your
  users just need a device that supports Apple Intelligence. With **no account setup, no
  authentication and no API keys**, this is really the easiest server LLM you'll ever use."
- 23: "**there are no token costs to you, the developer.**"
- 24–25: "**Each user gets a daily limit.** And users can **upgrade to iCloud+** to get higher limits."
- 26–27: "**This model is available for apps with less than 2M downloads.** And you can **apply on
  the developer website today**."

### A.2.1 The 2M-download gate — IMPORTANT, and NOT in the written docs

Line 26 is the single most consequential policy statement in the session and I could **not** find
it anywhere in the local written-doc corpus. The written article
(`repos/noemaai-labs__noema-ios/DocumentationforAPIs&SDKs/AppleFoundationModels/UsingPrivateCloudCompute.md:22-23`)
says only:

> "**IMPORTANT** — To develop with PCC you must meet certain eligibility requirements. To learn
> more and request access to the **managed entitlement**, see https://developer.apple.com/private-cloud-compute/"

So: transcript = "apps with less than 2M downloads"; docs = "certain eligibility requirements".
**Treat "< 2M downloads" as the transcript's concrete statement of that eligibility bar.**

Developer confusion about this is already live —
`forums/machine-learning-and-ai-foundation-models.txt` thread 834749 ("Accessing Private Cloud
Compute", 2026-06-15, lijiaxu): *"I am currently using a standard Developer Program account, and
it seems that I cannot apply for the program directly. Is there an alternative? Also, is there any
additional fee for using this service?"* — unanswered in the captured feed.

### A.2.2 Entitlement

`com.apple.developer.private-cloud-compute` — a **managed entitlement** (must be requested/granted;
you cannot just add it).

Confirmed in three independent local places:
- `…/AppleFoundationModels/UsingPrivateCloudCompute.md:139` — links
  `/documentation/BundleResources/Entitlements/com.apple.developer.private-cloud-compute`
- `…/AppleFoundationModels/Origami.md:148` — "Add the **managed**
  `com.apple.developer.private-cloud-compute` entitlement"
- Actual shipping entitlement plists in `repos/noemaai-labs__noema-ios/Noema/`:
  `Noema.entitlements:25`, `NoemaDirect.entitlements:15`, `NoemaVisionOS.entitlements:23`,
  `RelayServer.entitlements:15` — all carry the key.

The transcript never says the entitlement name aloud.

## A.3 The one-line switch

319:29–31:

> "If you already have an app using Foundation Models, you know that it takes just **3 lines of
> code** to prompt the on-device LLM. You create a session and then ask it to respond to your
> prompt. And now by changing just **1 line of code**, you can switch to the new server model on
> PCC."

**[RECONSTRUCTED — corroborated verbatim by docs]** The on-screen before/after is almost certainly:

```swift
// Before — on-device
let session = LanguageModelSession()
let response = try await session.respond(to: prompt)

// After — PCC  (the one changed line)
let session = LanguageModelSession(model: PrivateCloudComputeLanguageModel())
let response = try await session.respond(to: prompt)
```

Corroboration: `UsingPrivateCloudCompute.md:41-44` is byte-for-byte

```swift
// Create a session with the server-side model.
let session = LanguageModelSession(model: PrivateCloudComputeLanguageModel())
```

and shipping code `repos/noemaai-labs__noema-ios/Noema/AFMLLMClient.swift:288` does
`model: PrivateCloudComputeLanguageModel(),`.

319:32–35 on why this works:

> "With just that line, you're now talking to a much larger model, with larger context and more
> complex reasoning capabilities. The Foundation Models framework offers a **unified Swift API**,
> regardless of which model you're talking to. **Getting structured output with Generable, or
> calling Tools, works just the same with the PCC model, as it does with the on-device model.**
> This easily lets you switch between models, without having to rewrite your code."

The docs give the mechanism the transcript leaves implicit
(`UsingPrivateCloudCompute.md:39`): "Because both `PrivateCloudComputeLanguageModel` and
`SystemLanguageModel` conform to the **`LanguageModel`** protocol, you can pass either to
`init(model:tools:instructions:)`."

## A.4 Availability gating

319:36–37:

> "Keep in mind, **just like with the on-device model, PCC is only available on Apple Intelligence
> devices.** It's important to check the availability API, and gracefully handle when Apple
> Intelligence is not available on a user's device."

**Exact API surface (from docs + shipping code, NOT spoken in the transcript):**

`UsingPrivateCloudCompute.md:58-71`:

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

Shipping-code confirmation of the *same* enum cases, plus an `@unknown default:` arm
(`repos/noemaai-labs__noema-ios/Noema/AppleFoundationModelAvailability.swift:163-186`):

```swift
let model = PrivateCloudComputeLanguageModel()
switch model.availability {
case .available:
    let quota = model.quotaUsage
    if quota.isLimitReached {
        return .limitReached(resetDate: quota.resetDate)
    }
    if case .belowLimit(let information) = quota.status,
       information.isApproachingLimit {
        return .approachingLimit
    }
    return .available
case .unavailable(.deviceNotEligible): …
case .unavailable(.systemNotReady): …
case .unavailable: …
@unknown default: …
}
```

**OS version gate** (`UsingPrivateCloudCompute.md:46-54`): `PrivateCloudComputeLanguageModel` is
available on **iOS 27, macOS 27, watchOS 27, and visionOS 27 or later**:

```swift
if #available(iOS 27.0, macOS 27.0, watchOS 27.0, visionOS 27.0, *) {
    // Create a session using the server-based model.
} else {
    // Use the on-device model on older versions.
}
```

Note the shipping app's availability check omits watchOS and adds `visionOS 27.0`
(`AFMLLMClient.swift:91`): `if #available(iOS 27.0, macOS 27.0, visionOS 27.0, *)`.

**Doc-only extra guidance not in the transcript** (`UsingPrivateCloudCompute.md:56`):
> "Using PCC requires a network connection, so **if the request fails because the network
> connection is unavailable, retry the request using the on-device model.**"

**Also doc-only:** `PrivateCloudComputeLanguageModel` has a `supportsLocale(_:)` method — used at
`AFMLLMClient.swift:92-95`:

```swift
let model = PrivateCloudComputeLanguageModel()
guard model.supportsLocale(LocalizationManager.preferredLocale()) else {
    throw AFMLLMClientError.unsupportedLocale
}
```

(`SystemLanguageModel.default.supportsLocale(_:)` is gated at iOS/macOS/visionOS **26.4+** in the
same file, line 114-117.)

## A.5 On-device vs PCC — the comparison table

319:38–45, spoken as a table. Reconstructed exactly as narrated:

| | on-device `SystemLanguageModel` | `PrivateCloudComputeLanguageModel` |
|---|---|---|
| Privacy | ✅ ("They both offer privacy", 40) | ✅ |
| Works offline | ✅ | 🚫 requires internet (41) |
| Request limits | none (42) | daily limit per user (42) |
| Context size | **4K** (44) | **32K** (44) |
| Reasoning | not supported | supported, 3 levels (45) |

The docs table (`UsingPrivateCloudCompute.md:29-35`) matches **exactly** — same five rows, same
values, `Reasoning: Not supported / Multiple levels`, `Context size: 4K / 32K`.

### ⚠️ DISCREPANCY on the on-device 4K number

`repos/noemaai-labs__noema-ios/Noema/AFMLLMClient.swift:133-135` (a comment in shipping app code):

> "The on-device context is selected by the installed system model. **iOS 26 reports 4K while the
> iOS 27 model reports 8K.** `contextSize` is available in the Xcode 26.4+ SDK, so it must not be
> hidden behind the Xcode 27 gate."

So: the WWDC slide and the docs article both say **4K**, but real-device probing of
`SystemLanguageModel.default.contextSize` on iOS 27 reportedly returns **8192**. The app hardcodes
`4096` only as a fallback when `contextSize` returns `<= 0`
(`AFMLLMClient.swift:136-146`). **Do not hardcode 4096 — read `contextSize`.** (See A.7.)

PCC context limit is hardcoded as `32_768` in the same app
(`repos/noemaai-labs__noema-ios/Noema/AppleFoundationModelRegistry.swift:7`):

```swift
static let privateCloudContextLimit = 32_768
```

## A.6 Reasoning

319:46–52, the clearest plain-English definition Apple gives:

> "But what is reasoning? When an LLM responds to your prompt, it typically just reads the prompt
> and generates a response. With reasoning, **the model thinks before it generates the response.
> This literally happens by letting the model generate extra text, in a separate segment of the
> transcript.**
>
> The PCC model offers **3 levels of reasoning**. **Light** lets the model gather some extra
> context. **Moderate** lets the model reason a little deeper. And with **Deep**, the text for the
> reasoning segment may be **even longer than the actual response**."

319:53: "You can set the reasoning level **when calling `respond` on your session**."

**[RECONSTRUCTED — corroborated verbatim by docs]** `UsingPrivateCloudCompute.md:126-131`:

```swift
let response = try await session.respond(
    to: "What are the tradeoffs in this architecture?",
    contextOptions: ContextOptions(reasoningLevel: .deep)
)
```

Type path per docs links: `ContextOptions.ReasoningLevel` enum with cases
`.light`, `.moderate`, `.deep`
(`/documentation/foundationmodels/contextoptions/reasoninglevel-swift.enum/{light,moderate,deep}`).

Note the parameter is `contextOptions:` on `respond`, **not** `options:` (which is
`GenerationOptions`). 339:108–110 makes the split explicit — see B.6.

### Reasoning appears in the transcript, and you can observe it

319:54–55:

> "The **transcript of your session includes the reasoning segment.** You can **observe the
> transcript to show progress**, which is especially useful with the **Deep** reasoning level,
> which may take some time."

319:56–58 — the footgun:

> "But keep in mind, **reasoning is extra text that the model generates. So it uses tokens. This
> counts towards your context size limit.**"

Docs agree and add a nuance the transcript doesn't state
(`UsingPrivateCloudCompute.md:135`):

> "**Reasoning segments reflect the model's intermediate reasoning and don't appear in the final
> response content.** Reviewing them helps you understand why the model produced a particular
> answer, which is useful when debugging complex prompts."

Docs-only recommendation on picking a level (`UsingPrivateCloudCompute.md:133`):

> "To determine what reasoning level to use, evaluate your feature by **starting with `moderate`**.
> Use `deep` when you determine the task needs additional reasoning, like when you're making
> architectural decisions with many competing constraints. Deep reasoning is slower, but it spends
> more time catching things that the other levels miss."

Also seen composed into a Dynamic Profile (`…/AppleFoundationModels/Origami.md:151-163`) —
**note both a `.reasoningLevel(.deep)` modifier AND a `.contextOptions(...)` modifier appear**,
which looks redundant/possibly an error in that doc:

```swift
if #available(iOS 27.0, *) {
    let pccModel = PrivateCloudComputeLanguageModel()
    if case .available = pccModel.availability {
        Profile(model: pccModel) {
            TutorialInstructions()
        }
        .reasoningLevel(.deep)
        .contextOptions(ContextOptions(reasoningLevel: .deep))
    }
}
```

## A.7 `contextSize` — new programmatic API

319:59–60, verbatim:

> "Speaking of context size, we also added a convenient API to let you **programmatically get the
> context size for a model**. Just access the **`contextSize`** property on **either
> `SystemLanguageModel` or `PrivateCloudComputeLanguageModel`**."

Corroborated by shipping code `AFMLLMClient.swift:140`:

```swift
let reported = SystemLanguageModel.default.contextSize
if reported > 0 { return reported }
```

with the SDK-availability comment "`contextSize` is available in the **Xcode 26.4+ SDK**, so it
must not be hidden behind the Xcode 27 gate" (`AFMLLMClient.swift:134-135`). **So `contextSize`
predates the 27 SDK** even though it was announced in this 27-era session. It returns an `Int`
(token count), and defensive code treats `<= 0` as "unknown".

## A.8 "Data, not vibes" — evaluate before choosing

319:61–64, one of the strongest presenter recommendations in the whole set:

> "When deciding between the on-device and PCC model, or deciding the reasoning level to use, it's
> good to make that decision **based on data, not just vibes**. Evaluating let's you understand
> the quality of your specific feature. **You may be surprised how well the on-device model
> performs at certain tasks, especially with the updated model this year. But the only way to know
> is by evaluating.**"

319:65–68: the **Evaluations framework** is "a new Swift framework that helps you evaluate your
Foundation Models features. It's **integrated right in Xcode**" → session "Meet the Evaluations
framework".

Docs echo the ordering (`UsingPrivateCloudCompute.md:27`): "**Start with the on-device model and
evaluate it** with the Evaluations framework. **If you determine your feature needs more reasoning
capability or context size, then use PCC.**"

319:69 — cross-session pointer: "**you can even use the on-device and server model together!**
Check out '**Build agentic app experiences with Foundation Models**'."

## A.9 Handling usage limits — the whole UX chapter

319:70–73:

> "When using the PCC model in your app, it's important to handle usage limits well. **Requests are
> counted with your user's iCloud account.** And you can optimize your app for the case where a
> user hits a limit."

The demo app (319:74–76): "an app that summarizes an article using the PCC model. I can select a
**markdown file**, and we take the **text and images**, feed that into a `LanguageModelSession`,
and generate a summary. This works great with the large context size that PCC offers."
*(Note: text **and images** into PCC — so PCC accepts image attachments too, not just the on-device
model. UNVERIFIED whether image support on PCC has separate limits.)*

319:77–80:

> "But when a user hits a limit, **the request throws an error. If that error is just shown in the
> UI, that's not a great user experience, because it's not very actionable.** To handle this
> better, you can check for **`isLimitReached` on the `quotaUsage` of the model**. And handle that
> with custom UI in your app. Here I'm using a **label to go under my button**."

319:82–83: "when the user's limit is exceeded, you can **show a button to let the user manage their
limit**. For example, a user could **upgrade their account** to get a higher limit."

### The four explicit UI recommendations (319:84–88) — quote them

> "You should **integrate this with your existing UI**. **Avoid showing an alert for the usage
> limit. Because this UI should persist, and not be dismissed.** Instead, you can **update the
> state of your UI, like disabling the button that makes a request.** And under that button I'm
> showing a **subtle label**, with the button for letting the user get a higher limit, if they
> want."

319:89–90 — the *approaching* case:

> "You can also **detect the case where a user is approaching their limit**. This can be good to
> indicate to your users that they are close to their daily limit, so they can **make an informed
> decision for which requests they want to make**."

### The exact quota API

**[RECONSTRUCTED from transcript; verbatim in docs]** `UsingPrivateCloudCompute.md:82-103`:

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

Type surface, assembled from docs links + shipping code:

- `PrivateCloudComputeLanguageModel.quotaUsage` → `QuotaUsage` **struct**
  (doc path `privatecloudcomputelanguagemodel/quotausage-swift.struct`)
- `QuotaUsage.isLimitReached: Bool`
- `QuotaUsage.status` → enum with (at least) case `.belowLimit(Information)`;
  `Information.isApproachingLimit: Bool`
  (doc path `.../quotausage-swift.struct/status-swift.property`)
- `QuotaUsage.resetDate` — doc path `.../quotausage-swift.struct/resetdate`.
  Docs: "This value is **empty when the reset date isn't known or when the person is well below
  their limit**." (`UsingPrivateCloudCompute.md:105`)
- `QuotaUsage.limitIncreaseSuggestion` → optional; has `.show()`, which presents **system UI** for
  the iCloud+ upgrade. Shipping code checks `!= nil` to decide whether to even offer the affordance
  (`AppleFoundationModelAvailability.swift:199`, `:210`).
- Thrown error: `PrivateCloudComputeLanguageModel.Error.quotaLimitReached(_:)`
  (doc path `privatecloudcomputelanguagemodel/error/quotalimitreached(_:)`).

**Docs-only distinction worth memorizing** (`UsingPrivateCloudCompute.md:105`):

> "**Unlike rate limiting, where a person waits for a period of time before trying again, exceeding
> the daily quota means a person either waits for their usage quota to refresh or they upgrade to a
> higher tier.**"

## A.10 Xcode scheme option to simulate quota states

319:91–95:

> "In Xcode, we have a convenient **debug option to simulate the usage limit status. In your
> scheme, select **Debug** and then **Options**. Here we have the **Simulate Apple Foundation
> Models Availability** option. We can select **Quota Usage Limit Reached** … And we can also
> select **Nearing Usage Limit**."

**⚠️ Transcript vs docs naming discrepancy.** The docs
(`UsingPrivateCloudCompute.md:111-118`) give a different menu name and a different second option
label:

1. Choose **Product > Scheme > Edit Scheme**.
2. Select the **Run** page and choose the **Options** tab.
3. Select either "**Approaching Quota Usage Limit**" or "**Quota Usage Limit Reached**" from the
   "**Simulated Apple Foundation Models Availability**" drop-down menu.
4. Click Close and run your project.

| | transcript (319:92-95) | docs (`UsingPrivateCloudCompute.md:113-118`) |
|---|---|---|
| scheme page | "Debug" then "Options" | "**Run**" page → "Options" tab |
| menu title | "**Simulate** Apple Foundation Models Availability" | "**Simulated** Apple Foundation Models Availability" |
| limit-reached option | "Quota Usage Limit Reached" | "Quota Usage Limit Reached" ✅ same |
| approaching option | "**Nearing Usage Limit**" | "**Approaching Quota Usage Limit**" |

Trust the docs for the exact strings; the transcript is spoken from a beta build. The **menu
exists and has (at least) those two simulated states** — that much is agreed.

319:96–98 shows the second state being coded: "We already handled the `isLimitReached` case in the
code before. We can now also test the **`belowLimit`** case. Just like with `isLimitReached`, we
can show a simple label."

319:102: "**And all this took just a few lines of code.**"

## A.11 Session cross-references from 319

- 104: "apply on the Developer website today" (→ https://developer.apple.com/private-cloud-compute/)
- 106: "**What's new in the Foundation Models framework**" — start here for an overview
- 107: "**Debug and profile agentic app experiences with Instruments**"
- 68: "**Meet the Evaluations framework**"
- 69: "**Build agentic app experiences with Foundation Models**"

(319:108-109 is an outtake — "Where is that book? I need to bring it out to the library." — ignore.)

---

# PART B — WWDC26-339: bringing ANY LLM to the framework

Presenter: Christopher Webb, **Machine Learning Research team**. 213 lines. This is the
architecture session for the whole theme.

## B.1 Audience split

339:13–14:

> "**For app developers**, I'll show you how to call any of these models through the same familiar
> API. **For model providers**, I'll walk you through how to create a Language Model package of
> your own."

## B.2 The four-line preview (339:15–23)

Narrated as four consecutive swaps of one construction line.
**[RECONSTRUCTED — each corroborated by a different local source]**

```swift
// 1. On-device Foundation Model  (339:16-17)
let model = SystemLanguageModel()
let session = LanguageModelSession(model: model)
let response = try await session.respond(to: "…")

// 2. "If you need more horsepower, try Private Cloud Compute. Just swap the model." (339:19-20)
let session = LanguageModelSession(model: PrivateCloudComputeLanguageModel())

// 3. "If you want to ship your own model, just point CoreAI at your resources." (339:21)
let model = try await CoreAILanguageModel(resourcesAt: bundleURL)
let session = LanguageModelSession(model: model)

// 4. "if you want to try the latest open source models, simply pass in a model ID,
//     and let the framework handle the rest." (339:22)
let model = MLXLanguageModel(configuration: ModelConfiguration(id: "mlx-community/…"))
let session = LanguageModelSession(model: model)
```

Corroboration for #3 — `repos/apple__coreai-models/swift/Sources/CoreAILanguageModels/LanguageModel/CoreAILanguageModel.swift:23-30`
(Apple's own doc comment):

```swift
/// let model = try await CoreAILanguageModel(resourcesAt: url)  // .lazy by default
/// print(model.estimatedSizeOnDiskBytes ?? 0)
/// try await model.load()                                       // optional; respond auto-loads
/// let session = LanguageModelSession(model: model)
/// // ... generate ...
/// model.unload()
```

Corroboration for #4 — `repos/ml-explore__mlx-swift-lm/Libraries/MLXFoundationModels/MLXLanguageModel.swift:304-337`
(Apple/MLX doc comment; note the real initializer takes more than an ID):

```swift
import MLXFoundationModels
import MLXHuggingFace
import MLXLMCommon
import HuggingFace
import Tokenizers

let model = MLXLanguageModel(
    configuration: ModelConfiguration(id: "mlx-community/Qwen2.5-3B-Instruct-4bit"),
    capabilities: [.guidedGeneration, .toolCalling],
    weightsLocation: { id in … },
    load: { configuration, progressHandler in
        try await loadModelContainer(
            from: #hubDownloader(),
            using: #huggingFaceTokenizerLoader(),
            configuration: configuration,
            progressHandler: progressHandler)
    })
let session = LanguageModelSession(model: model, tools: [], instructions: nil)
let response = try await session.respond(to: "Hello!")
print(response.content)
```

> **Reality check on "simply pass in a model ID".** The shipping `MLXLanguageModel` init is
> `init(configuration:capabilities:configurationResolver:weightsLocation:load:)` — the ID alone is
> not enough; you inject a downloader and a loader. The `#hubDownloader()` /
> `#huggingFaceTokenizerLoader()` macros are what make the transcript's claim roughly true in
> practice. Also, `import MLXFoundationModels` confused developers at ship time — forums thread
> **836264** ("Bring an LLM provider to the Foundation Models, missing MLX dependencies", 2026-06-27)
> asks "Where is this framework, there are no BETA branches on the MLX framework either." Answer
> (from the local repo): it is the `MLXFoundationModels` library inside **`ml-explore/mlx-swift-lm`**,
> and it is compiled only under `#if FoundationModelsIntegration` + `#if canImport(FoundationModels, _version: 2)`.

339:23 — the payoff for using the protocol:

> "And using a model built on top of the Language Model protocol means you get access to **all
> kinds of great Foundation Models features, like Dynamic Profiles**."

## B.3 The four steps to ship a model package (339:27–34)

> "There are **four steps** to bring your model into the framework.
> 1. **Packaging.** 'A well-crafted Swift package makes it easy for developers to get started.'
> 2. **Implement the protocol** — 'by defining the types that describe your model and the
>    EXECutor that runs it.'
> 3. **Authentication** for server-based models, 'including some best practices'.
> 4. **Customization** — 'From attaching **response metadata**, all the way to defining entirely
>    **new modalities**.'"

*(The transcript's ASR consistently renders "executor" as "EXECutor"; that is a transcription
artifact, the type is `LanguageModelExecutor`.)*

## B.4 Step 1 — Packaging (339:35–49)

Four recommendations, each quoted:

1. **Use SwiftPM.** 339:36 — "We recommend using **Swift package manager** so that developers can
   simply add your package as a dependency of their app. We'll cover how to set up `Package.swift`,
   and how to publish a release."
2. **Support all four Apple platforms.** 339:40–41 — "Foundation Models supports **iOS, macOS,
   visionOS, and watchOS**, allowing developers to create a variety of experiences. **We recommend
   you try to do the same.**"
3. **Consider Linux.** 339:42 — "because the **Foundation Models framework is being released as
   open source**, your package could also be useful to developers who **deploy Swift on their
   servers**, so consider supporting **Linux** too."
4. **Mind your dependencies.** 339:43–45 — "Third, your dependencies. **Every dependency translates
   to bytes that a developer ships to their users. Carefully consider what dependencies are linked
   by your package.**"

Publishing (339:46–49):

> "Publishing your package is as easy as **creating a git tag**. Swift Package Manager is
> **decentralized, so your repo URL is your distribution channel.** Developers can paste the URL
> into Xcode and start integrating your model into their apps. For more, see '**Creating Swift
> Packages**'."

## B.5 Step 2 — The protocol

### B.5.1 The two pieces (339:50–58)

> 52–55: "The protocol has **two key pieces**. The first is **`LanguageModel`**. It **describes the
> model to the framework**. It declares **what the model can do, through capabilities**, and
> provides the **configuration** the framework needs to set up the model's executor."
>
> 56–57: "The second piece is **`LanguageModelExecutor`** where the work happens. It has **an
> initializer that takes a `Configuration`**, a **`prewarm`** function for preparing resources
> ahead of the first request, and a **`respond`** function that **streams generation back to the
> session**."
>
> 58: "**The `Configuration` is what links the two types: the Model provides it, and the framework
> uses it to construct the executor.**"

### B.5.2 The exact protocol text

The transcript says "Now you've **seen the protocol in code**" (339:59) but never reads the
signatures aloud. The following is **read from the macOS 27 beta
`FoundationModels.swiftinterface`** by the author of
`repos/john-rocky__coreai-model-zoo/knowledge/fm-provider.md:19-38` (that file explicitly says
"Two pieces (verified against the 27-beta `FoundationModels.swiftinterface`)"), and is consistent
with all three conforming implementations in this project's repos:

```swift
protocol LanguageModel: Sendable {
    associatedtype Executor: LanguageModelExecutor where Self == Executor.Model
    var capabilities: LanguageModelCapabilities { get }   // .vision/.guidedGeneration/.reasoning/.toolCalling
    var executorConfiguration: Executor.Configuration { get }
}

protocol LanguageModelExecutor: Sendable {
    associatedtype Configuration: Hashable, Sendable      // per-session executor cache KEY
    init(configuration: Configuration) throws
    func prewarm(model: Model, transcript: Transcript)    // careful: default no-op exists
    nonisolated(nonsending) func respond(
        to request: LanguageModelExecutorGenerationRequest,
        model: Model,
        streamingInto channel: LanguageModelExecutorGenerationChannel) async throws
}
```

Independent confirmation of every member, from three separate conformances:

| Member | Apple `CoreAILanguageModel` | MLX `MLXLanguageModel` | community `ZooLanguageModel` |
|---|---|---|---|
| `typealias Executor` | `public typealias Executor = CoreAIExecutor` (`CoreAILanguageModel.swift:57`) | nested `public struct Executor: LanguageModelExecutor` (`MLXLanguageModel.swift:666`) | `public typealias Model = ZooLanguageModel` on the executor (`ZooExecutor.swift:35`) |
| `capabilities` | `public var capabilities: LanguageModelCapabilities` (`:59`) | `public let capabilities: LanguageModelCapabilities` (`:520`) | declares `[.toolCalling]` |
| `executorConfiguration` | `:67` returns `CoreAIExecutor.Configuration(url:variant:kvCacheStrategy:modelIdentifier:samplingConfig:vocabSize:)` | `:528` returns `Executor.Configuration(modelID: modelID)` | keyed on `modelID` |
| `Configuration: Hashable` | struct with 6 fields | `public struct Configuration: Hashable, Sendable { public let modelID: String }` (`:877-880`) | custom `==`/`hash` on `modelID` only (`ZooExecutor.swift:37-49`) |
| `init(configuration:) throws` | yes | `public init(configuration: Configuration) throws` (`:886`) | `public init(configuration: Configuration) throws` (`:58`) |
| `prewarm(model:transcript:)` | `public func prewarm(model: CoreAILanguageModel, transcript: Transcript)` (`:269`) | `public func prewarm(model: MLXLanguageModel, transcript: Transcript)` (`:920`) | `public func prewarm(model: ZooLanguageModel, transcript: Transcript)` (`:82`) |
| `respond(to:model:streamingInto:)` | `public nonisolated(nonsending) func respond(...)` (`:275-279`) | `public func respond(...)` (`:938-942`) | `public nonisolated(nonsending) func respond(...)` (`:114-118`) |

**`LanguageModelCapabilities`** — an OptionSet-like value with a nested `Capability` type. Known
cases, verified across sources: `.vision`, `.guidedGeneration`, `.reasoning`, `.toolCalling`.

```swift
// repos/apple__coreai-models/.../CoreAILanguageModel.swift:59-65
public var capabilities: LanguageModelCapabilities {
    var caps: [LanguageModelCapabilities.Capability] = []
    if supportsToolCalling { caps.append(.toolCalling) }
    if supportsReasoning { caps.append(.reasoning) }
    if isGuidedGenerationSupported { caps.append(.guidedGeneration) }
    return LanguageModelCapabilities(caps)
}
```

Two init spellings exist: `LanguageModelCapabilities(caps)` (Apple's adapter, positional) and
`LanguageModelCapabilities(capabilities: capabilities)` (MLX, `:565`). Membership test is
`.contains(.vision)` (`MLXLanguageModel.swift:957`).

**Capabilities are load-bearing for routing, not decorative.** MLX's doc comment
(`MLXLanguageModel.swift:515-519`) is the sharpest statement of this anywhere:

> "Declaring `.reasoning` matters for **request routing**: the framework **only forwards a
> `reasoningLevel` to executors that declare `.reasoning`, and auto-rejects one otherwise (on the
> developer's behalf) before `respond` runs.** The executor in turn emits `.reasoning` events only
> when this capability was declared."

### B.5.3 The executor store — how Configuration becomes a cache key (339:59–66)

Narrated as an animated diagram. Verbatim:

> "Each **session holds an executor store**. When **Model1** arrives, the framework checks the
> store using the model's configuration, but there's no matching executor. So, the
> `LanguageModelSession` creates a new executor and stores it. **Model2 produces the same
> configuration, and because `Configuration` is `Hashable`, the framework knows it matches, and
> resolves to the same executor. The configuration is the lookup key, not the model.** Model3
> produces a different configuration, so it gets its own executor. **Each unique configuration maps
> to exactly one executor in the store.**"

339:67–71:

> "Here's a `LanguageModel` implementation. It declares its capabilities and returns the
> configuration the framework uses to find its executor. **The Executor is where the real work
> lives, loading weights, managing resources, and streaming tokens back to the session.** The
> framework constructs it from a configuration your model provides, then hands **the model in on
> every request**. **That split is what keeps your Model trivial to construct.**"

Practitioner note from `fm-provider.md:190-193` (trap 3):

> "**`Configuration` is the executor cache key.** The session stores executors keyed by your
> Hashable `Configuration` — key it by **bundle identity (+ anything that changes behavior)**.
> Apple keys by `(modelIdentifier, samplingConfig)`."

`ZooExecutor.Configuration` (`ZooExecutor.swift:37-49`) shows a legitimate trick: the struct holds
non-Hashable payload (`any InferenceEngine`, `any Tokenizer`, `any PromptDialect`) and implements
`==`/`hash(into:)` **on `modelID` alone** so it can still be a key.

### B.5.4 Lifecycle / teardown (339:72–74)

> "**When the session deallocates, the store goes with it. Every stored executor gets released,
> your `deinit` runs, weights are freed, and connections closed, all automatically. You don't write
> any of that teardown code yourself.**"

⚠️ In practice the MLX adapter still needs explicit eviction APIs
(`MLXLanguageModel.evictAll()` / `.evict()`, `:472`, `:484`) because it keeps a **process-global
`static let cache = ModelCache()`** (`:351`) *outside* the executor. That is the pattern for
"weights shared across sessions" and it deliberately opts out of the automatic teardown the
transcript describes. Note the doc comment there: "**Without caching, model loading takes 2-30
seconds per request.**" (`MLXLanguageModel.swift:349-350`)

### B.5.5 `prewarm` (339:75–82)

> "Within that lifecycle, your executor has one more function: **`prewarm`**. Before a request
> arrives, the developer can ask the framework to prewarm. It's your chance to do **expensive setup
> ahead of time, like loading weights, opening connections, or anything that would otherwise slow
> down that first response.**
>
> One approach is to put that setup in a **private helper that loads the weights once and caches
> them**. `prewarm` calls the helper **eagerly**, so the weights are ready before the first request
> arrives. **But `prewarm` isn't guaranteed to run.** Either way, weights load exactly once, and
> **if your executor has no expensive setup, like a server-backed model, `prewarm` can simply be a
> no-op.**"

Design constraints visible in every real implementation: **`prewarm` is synchronous and
non-throwing**, so all three conformances spawn a detached `Task`:

```swift
// repos/apple__coreai-models/.../CoreAILanguageModel.swift:269-271
public func prewarm(model: CoreAILanguageModel, transcript: Transcript) {
    Task { try? await resources.loadResources() }
}
```

```swift
// repos/ml-explore__mlx-swift-lm/.../MLXLanguageModel.swift:920-930
public func prewarm(model: MLXLanguageModel, transcript: Transcript) {
    Task {
        do {
            try await model.warmUp()
        } catch {
            Self.logger.error(
                "MLX prewarm failed for \(model.modelID, privacy: .public): \(error.localizedDescription, privacy: .public)"
            )
        }
    }
}
```

**🚨 THE #1 PROVIDER FOOTGUN — silent no-op `prewarm`.** The protocol ships a default no-op
extension, so a *near-miss* signature compiles and is never called. Two independent sources say so:

- `fm-provider.md:183-186` (trap 1): "**`prewarm` has a default no-op extension.** Implement
  `prewarm(model:transcript:)` *exactly* — implement `prewarm(transcript:)` and it compiles but is
  never called. **Apple's own adapter has this today**, which is why `session.prewarm()` does
  nothing for Core AI models: do your own warm-up (a 1-token generate after load)."
- `MLXLanguageModel.swift:901-907`: "The signature must match the requirement *exactly* —
  **concrete `Transcript`, not a generic `some Collection<Transcript.Entry>`** — otherwise it fails
  to bind as the witness and the framework's no-op default silently wins instead."
- `ZooExecutor.swift:68-70`: "the protocol ships a default no-op, so a near-miss compiles and is
  silently never called."

MLX's warm-up also documents a subtlety the transcript glosses: loading weights is **not** enough —
"Metal kernels **JIT-compile lazily on the first *synchronous* readback** (`.item()` inside the
generate loop) — scheduling work with `asyncEval` alone does not compile them — so this runs a
**minimal throwaway forward pass**" (`MLXLanguageModel.swift:598-601`). Its `preload()` is
explicitly weights-only: "**it runs no forward pass, compiles no Metal shaders, and performs no GPU
work, so the first generation request after `preload()` still pays the one-time Metal shader JIT
cost.**" (`:573-576`)

## B.6 What flows IN to `respond`

339:83–85:

> "Once your `respond` function is called, your executor goes to work. It **converts the transcript
> of the conversation into the format your model expects**. It **applies the options** the
> developer has set and it **streams generation events to the session**."

339:86–92 — the mental model:

> "From the developer's side, **the session is the entire interaction surface**. They initialize the
> model, create the session, call respond, and wait. Your executor and the rest of your package,
> all of that **lives behind the session, out of sight**. The developer never sees that machinery…
>
> The framework hands you **transcript entries**, but your inference engine can only process its
> **native types**. So your executor **sits in the middle, translates the entries into messages
> your inference engine understands**… When your inference engine answers, **the same translation
> runs in reverse: your messages back to transcript entries, streamed to the session.**"

### B.6.1 The Transcript (339:93–105)

> 94–96: "A transcript is **the conversation so far, expressed as a sequence of entries. Each entry
> plays a role.** **Instructions**, set by the developer, **prompts**, from the user, **tool calls**
> your model made, and the **outputs** they returned, and the **responses** your model has
> produced."
>
> 98: "**Foundation Models defines these six entry types.**"

Six entry kinds (the transcript names five in prose; the sixth is `reasoning`, named at 339:102 and
listed explicitly in `fm-provider.md:41-42`):

```
instructions | prompt | toolCalls | toolOutput | response | reasoning
```

Role-mapping guidance (339:99–105), quoted because it is the crux of provider work:

> "**Your model defines its own roles. Your executor's job is to map between the two, no matter the
> shape your model takes.**
>
> In this example, **instructions, prompt, and response map to system, user, and assistant.**
>
> Here, **tool calls, tool outputs, and reasoning all map to assistant too.** They're part of what
> the model did during its turn, and **since this model doesn't have dedicated roles for these, we
> just map them to assistant.**
>
> **If your model does define something like a dedicated tool role, you can route there instead.
> Either way, your executor stays in control.**"

Real-world corroboration that this mapping is per-family and non-transferable —
`fm-provider.md:208-213` (trap 9):

> "**Tool-prompt dialects don't transfer — render+parse each model's NATIVE format.** LFM2.5
> ignores in-context Hermes `<tool_call>`-JSON instructions and emits its trained special-token
> dialect (`<|tool_call_start|>[fn(arg=…)]<|tool_call_end|>`, pythonic) — **the training prior wins
> over the prompt.**"

### B.6.2 The request object and the two option bags (339:106–113)

> "**every request carries more than history, it carries the developer's intent for how the model
> should respond, expressed through two additional properties.**
>
> Every request object can include **`ContextOptions`** and **`GenerationOptions`**.
> **`ContextOptions` control what goes into the prompt, like the reasoning level you want the model
> to use, or a response schema. `GenerationOptions` control the decoder loop: sampling strategy,
> temperature, and maximum response length.**
>
> Here's what that looks like inside `respond`. Both types of options come in on the request, your
> executor pulls them out and passes them along when calling the model."

**`LanguageModelExecutorGenerationRequest` — verified member list** (assembled from the three
conformances; all reads shown are real call sites):

| Member | Type | Evidence |
|---|---|---|
| `.transcript` | `Transcript` (a `Collection` of `Transcript.Entry`) | `Array(request.transcript)` — `CoreAILanguageModel.swift:281`; `TranscriptConverter.mlxMessages(for: request.transcript)` — `MLXLanguageModel.swift:943` |
| `.enabledToolDefinitions` | tool definitions | `request.enabledToolDefinitions` — `CoreAILanguageModel.swift:284`, `MLXLanguageModel.swift:972`, `ZooExecutor.swift:139` |
| `.schema` | `GenerationSchema?` | `if let schema = request.schema` — `MLXLanguageModel.swift:977`; `if request.schema != nil` — `ZooExecutor.swift:120` |
| `.generationOptions` | `GenerationOptions` | `.maximumResponseTokens` (`MLXLanguageModel.swift:985`), `.samplingMode` (`:990`), `.temperature` (`:1221`), `.toolCallingMode` (`:969`, `ZooExecutor.swift:137`) |
| `.contextOptions` | `ContextOptions` | `request.contextOptions.reasoningLevel` — `MLXLanguageModel.swift:1110`, `:1154`, `:1186` |
| `.id` | `UUID` | `request.id.uuidString` stamped into metadata — `MLXLanguageModel.swift:1008` |

**Gotcha (`fm-provider.md:187-188`, trap 2):** "**`request.enabledToolDefinitions` is the property;
`enabledTools` is only the memberwise-init label.**"

**`GenerationOptions` — verified members:**
- `maximumResponseTokens: Int?`
- `temperature: Double?` (MLX clamps negatives to 0; `temperature == 0` routes to greedy —
  `MLXLanguageModel.swift:803-806`)
- `samplingMode: SamplingMode?` with `.kind` ∈ `{ .greedy, .randomTopK(k, seed), .randomProbabilityThreshold(threshold, seed) }`
  plus an `@unknown default` (`MLXLanguageModel.swift:812-826`). Construction sugar seen in app
  code: `GenerationOptions.SamplingMode.greedy` and `.random(top:seed:)`
  (`AFMLLMClient.swift:396-404`).
- `toolCallingMode: ToolCallingMode?` with `.kind` ∈ `{ .allowed, .disallowed, .required }`
  (`ZooExecutor.swift:137`, `MLXLanguageModel.swift:969`, `:1199`). Default when nil is `.allowed`.
  Cross-referenced to "WWDC26 242" in `ZooExecutor.swift:135`.

**`ContextOptions` — verified members:** `reasoningLevel` (`.light`/`.moderate`/`.deep`);
the transcript at 339:109 also says ContextOptions can carry "**a response schema**", though every
executor in this corpus reads the schema off `request.schema` rather than off `contextOptions`.
**UNVERIFIED** whether `ContextOptions` also exposes a schema field.

## B.7 What flows OUT — the generation channel

339:114–120:

> "On the response side, there are a few things to send: **the text your inference engine generates,
> any tool calls or reasoning, and the metadata that travels with them. They all go out as events
> on the channel.**
>
> Each chunk that the inference engine emits, a token or tool-call fragment, becomes an event. **A
> `textDelta`, a `toolCallDelta`, and so on.** The framework writes them to the transcript.
> **Foundation Models exposes both one-shot and streaming responses, but the implementation is
> always streaming; the one-shot API just collects the deltas internally.**"

> ⚠️ "textDelta"/"toolCallDelta" are the presenter's *conceptual* names. The **actual** channel
> event/action spelling, verified in three conformances, is `.appendText(_:tokenCount:)` /
> `.appendArguments(_:tokenCount:)` inside `.response` / `.reasoning` / `.toolCalls` events.

### B.7.1 The real channel API

`LanguageModelExecutorGenerationChannel.send(_:)` is `async`. Verified event/action shapes:

```swift
// text into the response segment
await channel.send(.response(action: .appendText(text, tokenCount: 1)))
await channel.send(.response(entryID: entryID, action: .appendText(text, tokenCount: 1)))

// reasoning segment (separate transcript entry)
await channel.send(.reasoning(action: .appendText(text, tokenCount: 1)))
await channel.send(.reasoning(entryID: entryID, action: .appendText(text, tokenCount: 1)))

// tool calls
await channel.send(
    .toolCalls(
        action: .toolCall(
            id: id, name: name,
            action: .appendArguments(argsJSON, tokenCount: 1))))

// metadata
await channel.send(.response(entryID: entryID, action: .updateMetadata(values)))

// usage
await channel.send(
    .response(
        action: .updateUsage(
            input: .init(totalTokenCount: promptTokens.count, cachedTokenCount: 0),
            output: .init(totalTokenCount: generatedTokenCount, reasoningTokenCount: reasoningTokenCount))))
```

Sources, line-exact:
- text/reasoning: `repos/apple__coreai-models/.../CoreAILanguageModel.swift:502-505`, `:512-514`,
  `:526-533`
- tool call: same file `:534-543`; and `MLXLanguageModel.swift:768-773`
- usage: same file `:468-476` and `:588-596`
- metadata: `MLXLanguageModel.swift:718`

Usage payload types (named in MLX's mirror enum, `MLXLanguageModel.swift:686-690`):
`LanguageModelExecutorGenerationChannel.Usage.Input` (`totalTokenCount:`, `cachedTokenCount:`) and
`…Usage.Output` (`totalTokenCount:`, `reasoningTokenCount:`).

Metadata value type, from MLX's emit helper signature (`:713-715`):
`[String: any Sendable & Codable & Equatable]`.

The `entryID:` parameter is optional on `.response`/`.reasoning` and **required on `.toolCalls`**
in MLX's helper (`:763-766`). MLX allocates three separate UUIDs per turn
(`MLXLanguageModel.swift:995-997`) with this comment:

> "**response and tool-calls entries each need a fresh UUID — they live in separate transcript
> entries.** We preserve the framework-supplied `request.id` for tracing by stamping it into the
> response metadata below, rather than reusing it as an entry id."

### B.7.2 The prescribed event ORDER (339:121–130) — a direct recommendation

This is the most actionable paragraph in the session. Verbatim:

> "put yourself in the developer's seat for a moment. They've called respond and they're waiting.
> What do they need first? Here's your executor's side of the handshake with the developer.
> **There's a deliberate order to it.**
>
> **First, a metadata update, model and request IDs the developer can use for logging and
> debugging.**
>
> **Then a usage update, prompt token counts for accounting. Sending these upfront means the
> developer isn't waiting through the whole stream to learn what each request costs.**
>
> **Finally, for each token your model produces, send a text delta the moment it arrives.** The
> framework streams those deltas to the session as they arrive, so users see the response appear
> word-by-word instead of all at once."

**Prescribed order: `updateMetadata` → `updateUsage` (prompt tokens) → N × `appendText`.**

MLX follows the metadata-first half exactly (`MLXLanguageModel.swift:1006-1009`):

```swift
// Send metadata first
await Self.emitMetadata(
    ["modelID": modelID, "requestID": request.id.uuidString],
    entryID: entryID, into: channel)
```

### 🚨 B.7.3 A verified BETA CONTRADICTION of that advice

`fm-provider.md:129-132` (and repeated at `ZooExecutor.swift:14-18`), verified on macOS 27.0 beta:

> "**Don't send WWDC-339-style upfront usage/metadata.** A `.response(updateUsage:)` event on a
> turn that ends in tool calls **materializes an EMPTY `Response` transcript entry.** Send metadata
> + usage **once at end of turn**, attached to the **kind of entry the turn produced**."

Apple's own `CoreAILanguageModel` executor also sends usage **at the end**, not upfront
(`CoreAILanguageModel.swift:468-476` runs after the generation loop and the parser flush). So:
**the transcript's recommended order is not what Apple's own adapter does, and following it
literally produces an empty transcript entry on tool-calling turns in the 27.0 beta.**

### 🚨 B.7.4 A verified SDK/dylib symbol mismatch on `updateUsage`

`MLXLanguageModel.swift:729-761` — long comment, worth quoting because it will bite anyone writing
a provider on this beta:

> "the FM-27 beta `.swiftinterface` declares
> `Response.Action.updateUsage(input:output:metadata: = [:])` (three parameters), but the **shipping
> FoundationModels dylib only exports the older two-parameter `Response.Action.updateUsage(input:output:)`**
> Because our call relies on the `metadata:` default, the compiler resolves it to the
> three-parameter symbol, **which does not exist at runtime.** dyld cannot bind it: under
> **chained-fixups linking (the arm64 default) the reference aborts the process the moment the
> image loads**, and under lazy binding it **faults through null (SIGSEGV at 0x0)** the instant this
> send executes — crashing every `respond()` path right after generation completes.
>
> **A runtime `dlsym` guard cannot save this**: the compiled reference to the missing symbol is
> enough to abort at launch regardless of any surrounding check. The only safe option is to **not
> reference the symbol at all**."

MLX's workaround: do not call `channel.send(.updateUsage(...))` at all on this SDK. Effect:
"consumer-visible usage for these responses may be absent or zero."

## B.8 Statefulness and transcript diffing (339:131–142)

> "Earlier we saw how the framework **caches executors by configuration**. **If your integration is
> stateful, holding a KV cache or persistent session between calls, that caching is what lets you
> minimize network churn and avoid redoing work.**
>
> **Your executor receives the full transcript on every call to `respond`.** Here's what you
> processed last time, an instruction, a prompt, and the response you generated.
>
> When the next call comes in you **compare the new transcript to the one you saved from last
> time**. **In most cases, new entries have simply been appended**, a new prompt after the last
> response. When that's the case, you can **preserve your existing state and only process what's
> new**.
>
> **But sometimes your comparison finds that entries have been removed or modified, for example,
> when the developer trims older entries to save context. When that happens, you'll need to
> invalidate back to where the transcripts diverge.**
>
> **The framework gives you the full transcript on every call. Your executor decides what counts as
> a match, and how to handle any changes.**"

Real implementation of exactly this — `ZooExecutor.swift:145-160`, the "append-only KV fast path":

```swift
// 3) Append-only KV fast path: skip reset and feed only the suffix
//    when the rendered prompt extends what's already in the cache.
let fed: [Int32]
let kvBase: [Int32]
if let kv = kvTokens, kv.isEmpty {
    fed = promptTokens
    kvBase = []
} else if let kv = kvTokens, promptTokens.count > kv.count,
    promptTokens.starts(with: kv)
{
    fed = Array(promptTokens[kv.count...])
    …
```

Measured payoff (`fm-provider.md:87`): "turn 2 **reused 97 cached tokens and prefilled 18**,
per-turn latency **flat at ~0.33 s instead of growing with history**." And the cost of NOT doing it
(`fm-provider.md:198-200`, trap 6): "**Multi-turn re-prefill tax.** Until an executor implements
transcript diffing, budget ~decode-speed × history-tokens per turn … measured: **turn 1 = 0.41 s,
turn 2 = 2.8 s** on the 0.8B with a 3-entry history + hidden thinking."

Two structural blockers on the diff approach, also from `fm-provider.md:87` and `ZooExecutor.swift:22-33`:
1. "the engine **over-generates past EOS into the cache**" — breaking out of a token stream does
   **not** stop a pipelined engine; post-EOS tokens land in the KV cache and poison the prefix match.
2. "**thinking models' templates strip historic `<think>` blocks the cache still contains**" — so
   the re-rendered prompt no longer prefixes the cache.

Both force a reset + full re-prefill. Correctness first.

## B.9 Approximate or throw (339:143–156)

> "**Sometimes your model can't do exactly what the developer asked. When that happens, your
> executor has two choices: approximate or throw.**
>
> **Be flexible where you can, and honor the developer's intent.**
>
> But sometimes there's no honest approximation. **If a developer sets a token limit, but also
> specifies a schema with required fields, there might not be a way to satisfy both. So you throw.**
>
> Foundation Models ships **`LanguageModelError`** for exactly these cases: **context window
> overflows, rate limits, refusals, and more.** Throw one of these, and **any developer who's used
> the framework already knows how to handle it**."

On custom errors (339:151–156) — the balance recommendation:

> "When the built-in `LanguageModelError` cases don't cover your situation, define your own error
> type. Some failures only make sense in the context of your service: **your subscription tiers,
> your features, your account states.** A purpose-built case name carries the intent…
>
> **Custom errors are powerful, and sometimes you need them. But each one is a new case developers
> must learn, catch, and handle in their app. Try to use a built-in `LanguageModelError` when it
> fits, and save the custom ones for failures only your service can produce.**"

### Verified `LanguageModelError` cases (from real throw sites)

| Case | Payload | Source |
|---|---|---|
| `.unsupportedCapability(_:)` | `LanguageModelError.UnsupportedCapability(capability:debugDescription:)` | `MLXLanguageModel.swift:960-965`, `:1065-1070`; `ZooExecutor.swift:121-127` |
| `.unsupportedTranscriptContent(_:)` | `.init(unsupportedContent: [Transcript.Entry], debugDescription: String)` | `CoreAILanguageModel.swift:293-298` |
| `.unsupportedGenerationGuide(_:)` | `.init(schemaName: String?, debugDescription: String)` | `MLXLanguageModel.swift:868-870` |
| `.contextSizeExceeded` (named, not shown at a throw site) | — | `spotlight-rag-third-party.md:89` |

Example — the "throw rather than fake it" rule, applied:

```swift
// repos/john-rocky__coreai-model-zoo/swift/Sources/ZooFMProvider/ZooExecutor.swift:119-128
// Pipelined zoo bundles sample on-GPU — no logits, no constrained
// decoding. Approximate-or-throw rule: there is no honest
// approximation of a schema, so throw.
if request.schema != nil {
    throw LanguageModelError.unsupportedCapability(
        .init(
            capability: .guidedGeneration,
            debugDescription:
                "GPU-pipelined zoo bundles sample on-device and expose no logits; "
                + "guided generation needs a sequential engine."))
}
```

And a nice worked example of *when NOT to* map an error to a typed case
(`MLXLanguageModel.swift:855-864`):

> "`constraintCompilationFailed` is **deliberately NOT mapped** to `unsupportedGenerationGuide`:
> its origin is ambiguous… and **claiming user-fault when the cause is actually our infrastructure
> misleads developers who pattern-match on typed errors.**"

## B.10 Step 3 — Authentication (339:157–167)

Short but pointed. Verbatim:

> "**Your job as a package author is to make it easy for developers to do the right thing. If your
> initializer takes an API key as a string, developers will be tempted to take the path of least
> resistance. Instead, help developers do the right thing by offering a token provider or sign in
> flow.**
>
> **And if your package fetches access tokens on behalf of developers, make sure to persist them
> securely using Keychain.**
>
> Credential handling is half the story. **Device attestation is the other half.** If you're
> shipping a **cloud-based `LanguageModel` package, this is worth a deep look.**
>
> This related session walks through **verifying the device, catching tampered builds, signing
> payloads, and using Apple's fraud signal to keep bad traffic off your service.** Check it out in
> '**Secure your apps with App Attest**'."

Concrete takeaways for a server-backed provider package:
1. **Do NOT** expose `init(apiKey: String)` as the primary path.
2. **DO** offer a **token provider** closure or a **sign-in flow**.
3. **DO** persist fetched tokens in **Keychain**.
4. **DO** integrate **App Attest** (device attestation, tampered-build detection, payload signing,
   Apple's fraud signal).

*(ASR renders it "at-test-ation"; the technology is App Attest / DCAppAttestService.)*

## B.11 Step 4 — Customization

### B.11.1 Response metadata (339:171–178)

> "The protocol gives you room to **shape `LanguageModelSession` around the abilities only your
> model offers**. **Response metadata is a lightweight option** to attach additional information to
> your responses…
>
> Here, after streaming completes, our executor sends **`tokensPerSecond`** and
> **`timeToFirstToken`** through the channel.
>
> **We recommend providing utilities or documentation that make it easy for developers to work with
> your metadata; clear keys, typed accessors, whatever makes sense.** Underneath, **metadata is just
> a dictionary. It can contain strings, numbers, and other built-in types.**"

**[RECONSTRUCTED]** the on-screen snippet, in the verified action spelling:

```swift
await channel.send(
    .response(
        entryID: entryID,
        action: .updateMetadata([
            "tokensPerSecond": tokensPerSecond,
            "timeToFirstToken": timeToFirstToken,
        ])))
```

Real analogue (`MLXLanguageModel.swift:1007-1009`): `["modelID": modelID, "requestID": request.id.uuidString]`;
and `:1228-1229` shows a Bool value: `["incompleteOutput": true]`.

### B.11.2 Custom segments — the extension point for NEW MODALITIES (339:179–189)

The single most forward-looking API in the session. Verbatim:

> "**Custom segments are the answer.** You'll **define a new segment type, receive it in your
> executor, and stream results back through the same channel**, and the developer **never has to
> leave `LanguageModelSession`** to use them. **Custom segment types let you extend the protocol.
> When a new modality comes along, audio, video, whatever's next, developers have a typed,
> structured way to send that data to your model.**
>
> Here's how it works. First, you'll **define a type that conforms to custom segment. Because
> custom segments are required to be `PromptRepresentable`, developers can pass it directly in
> their prompts, just like text.**
>
> In your executor, you'll **receive this as a `customSegment` in the transcript, alongside the text
> entries you're already handling.** When your model responds, you **emit the result back through
> the channel as a custom segment update.**
>
> **The segment ID controls whether you're adding a new segment, or updating one you've already
> started streaming. This gives you full control over how results stream into the app.**"

Facts to carry forward:
- Protocol name spoken as "custom segment" → **`CustomSegment`** (exact spelling **UNVERIFIED**;
  no local source implements one).
- Conformance requirement: **`PromptRepresentable`** — so a custom segment can be dropped straight
  into a `Prompt` builder.
- Received in the executor as a **`.customSegment`** transcript entry/segment.
- Emitted back as a **custom segment update** event on the same channel.
- **Segment ID semantics: new ID = new segment; reused ID = update an in-flight streamed segment.**

### B.11.3 Server-side tools — three levels of surfacing (339:190–203)

> "**Server-side tools are capabilities your model runs on its own, like web search, code
> execution, or image generation. The model invokes them, the server runs them, and your executor
> watches the results stream in.** We'll walk through **three levels of detail**, each surfacing
> more of the tool's work, using **web search** as an example.
>
> **Server-side tools are named, typed values on your model. The developer constructs the model with
> the tools they want, and your executor receives them through the model on every request, the same
> way it receives every other capability the model declares.**"

*(Note the architectural point: server-side tools live on the **model**, not on the session's
`tools:` array — that array is for Swift `Tool`s the framework executes locally.)*

**Level 1 — invisible grounding (339:196–198):**
> "the simplest pattern: **run the tool privately and stream only the answer back. The tool grounds
> the model's response, but its work stays inside your executor.** Each text delta you append gets
> streamed into the transcript by the framework, **with no trace of the tool that produced it.**"

**Level 2 — text + metadata, e.g. citations (339:199–200):**
> "In addition to grounding the answer on the tool's output, you can also **attach additional
> metadata to the response**. **When a text delta carries metadata, like a citation, forward both
> to the channel, and the framework attaches the metadata to the text segment in the transcript.**"

**Level 3 — surface the tool's own structured work (339:201–203):**
> "you can choose to **surface the tool's work itself. With custom segments, you forward the tool's
> structured output to the channel, alongside the text and any metadata, giving apps everything the
> model produced along the way.**
>
> **Through one channel, the events you forward, the metadata you attach, and the custom segments
> you design, server-side tools shape what apps using your package can show their users.**"

### B.11.4 The privacy-disclosure recommendation (339:204–205)

Final substantive point of the session, and it applies to BOTH sides of the ecosystem:

> "There's one more thing to keep in mind: **whether you're choosing a package or shipping one, make
> sure everyone in the chain understands the privacy implications of the model behind it. On-device
> and cloud-based models have very different privacy characteristics, and your users deserve to
> know which they're getting.**"

## B.12 Closing cross-references (339:206–213)

- "**Integrate On-Device AI Models into Your App Using Core AI**" — "for bundling local models
  directly into an app."
- "**Build with the new Apple Foundation Model on Private Cloud Compute**" — "goes deep on
  server-scale inference with Apple's privacy guarantees." ← **this is WWDC26-319's official title.**
- "**Build agentic app experiences with the Foundation Models framework**" — "shows how developers
  use **dynamic profiles** to build multi-step, tool-using workflows on top of models like yours."
- 212: "**We hope to see a thriving ecosystem of `LanguageModel` packages, giving Swift developers
  the freedom to choose the model that's right for their app.**"

---

# PART C — WWDC26-246: Spotlight + Foundation Models (`SpotlightSearchTool`)

Presenter: Jennifer, Spotlight engineering team. 138 lines. Demo app: a **hiking trails app**.

## C.1 The premise (246:1–18)

> 2–3: "This year, we're taking search to a whole new level, with Foundation Models and Core
> Spotlight. **You can build rich, conversational experiences in your app, simply by making your app
> content available to a large language model for reasoning and response generation.**"

The narrative problem (246:10–13):

> "By introducing a language model session into the app, I can ask broad questions, and **the model
> will answer just by drawing on its own knowledge of the world.** Now, **I really only want answers
> about hikes that my app knows about.** And this is where Spotlight can help. The hiking trails app
> has **indexed all these great hikes into a Core Spotlight search index**."

The mechanism (246:14–17):

> "to help the model answer questions about those particular hikes, we can use the app's Core
> Spotlight search index, **through tool-calling from the Foundation Models framework.**
>
> **The `Tool` protocol from Foundation Models is a powerful concept that can be used to extend a
> model's capabilities, both by taking actions for a request, or by looking up context that a model
> needs to generate a response.** A tool works by **declaring its arguments and output, along with
> some instructions on what the tool does.** And then, when the model decides it needs to use a
> tool, **it will simply generate the arguments to call up that tool, and use that output for
> response generation.**"

## C.2 `SpotlightSearchTool` — the announcement (246:19–21)

> "today, we're introducing **`SpotlightSearchTool`**. It's a tool that **adopts the tool protocol**,
> to let a language model **directly search your app's content in Core Spotlight** for contextual
> response generation.
>
> **`SpotlightSearchTool` is available on iOS, iPadOS, macOS, and visionOS.**"

**⚠️ watchOS is NOT in that list** — contrast PCC (319:9) which explicitly includes watchOS.

**Where the symbol lives** (NOT stated in the transcript;
`repos/john-rocky__coreai-model-zoo/knowledge/spotlight-rag-third-party.md:12-13`):

> "`SpotlightSearchTool` lives in the **`_CoreSpotlight_FoundationModels` overlay** — it
> **materializes when a file imports BOTH `CoreSpotlight` and `FoundationModels`**."

That matches 246:40: "We'll start by **importing both `CoreSpotlight` and `FoundationModels`**."

## C.3 Prerequisite: donate content first (246:22–24)

> "Before we get started, you'll want to make sure your app **donates searchable content with Core
> Spotlight**. Take a look at our past session on '**Supporting semantic search with Core
> Spotlight**', where we talk through **how to donate searchable content to Spotlight, how to manage
> donations with a delegate and reindex extension, and how to perform structured search over item
> attributes, and search against the semantic index.**
>
> **Once your app has donated searchable items to Core Spotlight, or indexed entities for Apple
> Intelligence, we're ready to begin.**"

("or **indexed entities for Apple Intelligence**" is an interesting second on-ramp — App Intents
entity indexing also feeds this. **UNVERIFIED** how that path differs.)

## C.4 Video agenda (246:25–27)

1. provide `SpotlightSearchTool` to your session
2. customize it with **guidance**, **knowledge providers**, and **specialized capabilities**
3. evaluate model responses with the **Evaluations framework**

## C.5 Basic adoption — three sub-steps (246:35–45)

> "There's **three things** we'll look at when adopting `SpotlightSearchTool`. We'll need to
> **configure the tool**, for the kind of search we want the model to perform. Then we'll want to
> **add additional context to the model, while the search is active**, to get the best response. And
> finally, we'll explore different ways to **display results** in our app's user interface."

246:39–43:

> "Configuring the tool is **not too different from performing a Spotlight query directly**. We'll
> start by importing both `CoreSpotlight` and `FoundationModels`. Then, **in one line of code, the
> tool is ready to search your app's Core Spotlight index.** You can also provide
> `SpotlightSearchTool` with a **custom configuration**. Here we're specifying a **`FileSource`** to
> perform a search against **file paths in your app's sandbox**."

246:44–45:

> "Next you'll want to **choose the right model for your app, whether it's the `SystemLanguageModel`
> or a model of your choosing, which you can do using the new Model Provider APIs.** Once you've
> chosen the model, **add the new `SpotlightSearchTool` instance to your `LanguageModelSession`** to
> start getting a response."

← **This is the explicit link between session 246 and session 339.** The tool is model-agnostic.

**[RECONSTRUCTED]** minimal form — corroborated by a real forum post
(`forums/machine-learning-and-ai-foundation-models.txt:31-37`, thread 838904):

```swift
import CoreSpotlight
import FoundationModels

let tool = SpotlightSearchTool()

let session = LanguageModelSession(tools: [tool])

let response = try await session.respond(to: "What hikes have I gone on?")
```

Configured form — **verified shape** from
`repos/john-rocky__coreai-model-zoo/knowledge/spotlight-rag-third-party.md:19-27`:

```swift
let tool = SpotlightSearchTool(configuration: .init(
    sources: [.coreSpotlight(CoreSpotlightSource(searchableIndexDelegate: delegate))],
    guide: SpotlightSearchTool.Guide(level: .focused(.items), format: .compact),
    contactResolver: nil,
    customStages: []))

// Behind YOUR model instead of the system one:
let session = LanguageModelSession(model: kitModel, tools: [tool], instructions: …)
let answer = try await session.respond(to: "What did I write about the night hike?")
```

**Verified `SpotlightSearchTool` API surface** (same file, `:30-37`):

- `Configuration.sources`: `.coreSpotlight(CoreSpotlightSource(...))` (your app's index) and/or
  `.files` (indexed files) — the transcript's "`FileSource`" (246:43) is the `.files` source.
- `Guide.level`: `.complete` | `.focused(ContentDomain = .items)` | `.dynamic(GuidanceProfile)`
- `Guide.format`: `.structured` | `.compact`
- `GuidanceProfile(textMatch:similarityMatch:numericMatch:dates:people:contentType:attributes:)`
- `tool.searchResults` is an `AsyncSequence<SearchReply, Never>`
- `CustomStage: Generable & Codable & Sendable` with `inputTypes`/`outputTypes` and
  `execute(items:/scoredItems:/count:/table:/text:…)`
- `CoreSpotlightSource(searchableIndexDelegate:)`, `CoreSpotlightSource(fetchAttributes:)`

## C.6 The tool-call trajectory (246:46–48)

> "It feels like magic, but **the response follows a path of tool calling and generation.** For a
> question like: *What hikes have I gone on?*, the trajectory might start with
> 1. **the model deciding it needs to use `SpotlightSearchTool`**
> 2. **the model will invoke the tool with a generated query**
> 3. **Spotlight will execute that query and return a description of the result set back**
> 4. **the model will reason over that output and generate its final response.**"

Independently observed trajectory on a third-party model
(`spotlight-rag-third-party.md:47-51`):

```
prompt → reasoning → toolCall spotlight_search({"searchTerms":["night hike"]})
       → toolOutput (items) → toolCall fetch_note({"id":"note-003"})
       → toolOutput (body) → grounded answer
```

→ the internal tool name is **`spotlight_search`** and its argument schema includes
**`searchTerms: [String]`**.

## C.7 🚨 THE BIG GOTCHA — the index does not give the model your text

246:49–51, verbatim:

> "**You might notice from some responses, that the model was not able to see all of the metadata,
> that was donated for the items. That's because some metadata in the Spotlight index, like text
> content and HTML, is stored in a highly-compact representation that can be searched, but not
> recovered in a way that a language model can read it.** For these cases, you'll want to consider
> **providing additional metadata for an item, while `SpotlightSearchTool` is performing a
> search.**"

Field-verified elaboration (`spotlight-rag-third-party.md:53-64`) — read this, it is more specific
than Apple's phrasing:

> "**The central gotcha: the tool returns metadata, not the body.** Even with
> `CoreSpotlightSource(fetchAttributes: [.title, .contentDescription, .keywords])`, the `toolOutput`
> handed to the model carries **only identity attributes** — `uniqueIdentifier`, `title`,
> `contentType`, `contentCreationDate`, `domainIdentifier`. **`contentDescription` and `keywords`
> do not appear** (in `.compact` or `.structured`). This is **not** a Spotlight limitation: a raw
> `CSSearchQuery` with the same `fetchAttributes` returns `contentDescription` (full body) fine
> (`textContent` is index-only — write-only for full-text search, returns nil on read).
>
> Consequence: **a model answering from search results alone sees only TITLES and will hallucinate
> bodies** (the system model, asked about a night hike, invented 'rained heavily / pack a waterproof
> jacket'; the real note said the headlamp died — pack spare batteries)."

### Apple's answer: the index-delegate hydration hook (246:52–57)

> "If your app donates searchable content to Core Spotlight, you'll already be familiar with the
> **index delegate protocol**. Your app would set an index delegate on your **`CSSearchableIndex`**
> to handle reindex requests, such as when Spotlight needs to perform migration or recovery.
>
> **For `SpotlightSearchTool`, we've added a method to the delegate to recover the full
> `CSSearchableItem` by its unique identifier.** This allows the model to **efficiently manage
> responses over potentially millions of results**.
>
> On your index delegate, simply adopt the new **`searchableItems(forIdentifiers:)`** to return the
> complete `CSSearchableItem`.
>
> **If your app has metadata that doesn't make sense to donate for search, but might be useful for
> the model to reason about, this is the right time to set any additional attributes on an item for
> the model to see.**"

**[RECONSTRUCTED]** delegate shape:

```swift
extension MyIndexDelegate: CSSearchableIndexDelegate {
    func searchableItems(forIdentifiers identifiers: [String]) -> [CSSearchableItem] {
        identifiers.compactMap { id in
            guard let trail = store.trail(id: id) else { return nil }
            let attrs = CSSearchableItemAttributeSet(contentType: .content)
            attrs.title = trail.name
            attrs.contentDescription = trail.notes          // <- the body the model needs
            // …plus any model-only attributes not worth indexing for search
            return CSSearchableItem(uniqueIdentifier: id,
                                    domainIdentifier: "trails",
                                    attributeSet: attrs)
        }
    }
}
```

⚠️ **Contradicting field note** — `spotlight-rag-third-party.md:116-118`:

> "`CSSearchableIndexDelegate` conforms and wires via `CoreSpotlightSource(searchableIndexDelegate:)`;
> `searchableItems(forIdentifiers:)` (**macOS 15.4+**, with a **new `protectionClass` overload in
> 27.0**) is the **index-recovery hydration API — not the search-time body path.**"

So: the method **pre-dates** this year (macOS 15.4+), got a new 27.0 overload with a
`protectionClass` parameter, and — in that author's 27.0-beta testing — did **not** actually
hydrate bodies into the tool output. **Treat 246:54-57 as the intended design and verify empirically.**

### The pattern that actually works today (field-verified, not in the transcript)

`spotlight-rag-third-party.md:66-85` — **retrieve with Spotlight, hydrate with your own `Tool`**:

```swift
struct FetchNoteTool: Tool {
    let name = "fetch_note"
    let description = "Read the full saved text of a note by its identifier."
    @Generable struct Arguments {
        @Guide(description: "The note id from spotlight_search, like note-002.") var id: String
    }
    func call(arguments: Arguments) async throws -> String { store[arguments.id] ?? "not found" }
}
let session = LanguageModelSession(model: kitModel, tools: [spotlightTool, FetchNoteTool()], …)
```

> "The model chains `spotlight_search` → ids/titles → `fetch_note(id)` → body → grounded answer.
> This mirrors a real app (**Spotlight index = lightweight finding aid; full content = your
> store**). **Verified on the system model, zoo qwen3.5-0.8B, and qwen3-4B.**"

## C.8 Displaying results — `searchResults` / `SearchReply` / `queryToken` (246:58–67)

> "**The session response is a concise description over the result set.** And in an assistant-style
> interface, **this response is typically what an app would want to display.**
>
> **But search results are also available directly on `SpotlightSearchTool` itself. For a list-style
> display, this is the best way to access searchable items, especially when the result set is
> large.** **Search replies pass back results in batches during the search, so query tokens can be
> used to manage the conversation stream, ensuring that user interface stays up-to-date with the
> model.**
>
> To access results from the `SpotlightSearchTool`, your app can **wait for search replies and check
> for `CSSearchableItem` in the content of the reply. Search replies come as an async sequence of
> events, where each reply may include a batch of results, until the tool call completes.**
>
> **Keep in mind that for any given response, the model may call `SpotlightSearchTool` MORE THAN
> ONCE, before generating its final response. For that reason, use the `queryToken` on each reply,
> to determine when the user interface should refresh.**"

**[RECONSTRUCTED]** consumption pattern:

```swift
Task {
    for await reply in tool.searchResults {
        if reply.queryToken != currentQueryToken {
            currentQueryToken = reply.queryToken
            items.removeAll()                 // new tool call → new result list
        }
        if case .items(let searchableItems) = reply.content {
            items.append(contentsOf: searchableItems)
        }
    }
}
```

**Verified `SearchReply` content kinds** (`spotlight-rag-third-party.md:34-35`):

> "`tool.searchResults` is an `AsyncSequence<SearchReply, Never>` — observe results live
> (**items / scoredItems / groupedItems / count / table / statistic / text** + **label** +
> **queryToken** + **status**)."

The `label` field is the one described at 246:108: "**each reply comes with a handy LLM-generated
label describing the content**, giving your app the most flexibility for its user interface."

## C.9 Customization axis 1 — Guidance profiles (246:68–80)

> 68: "`SpotlightSearchTool` provides a **host of search capabilities, from semantic search over
> text, to structured search over metadata, like dates, persons, locations and more.**"
>
> 69–73: "depending on the **language model you choose**, you may want to customize
> `SpotlightSearchTool` **both for the model, and your app content**. There's a few ways…
> **Guidance profiles** can be used to **scope the tool's search capabilities**. Providing the tool
> with **world knowledge** can help with **reference resolution**. And implementing **custom
> pipeline stages**, can **improve model reasoning over your app's content**."
>
> 74–79: "`SpotlightSearchTool` provides its **entire set of search capabilities** to a model for
> guided generation. But **guidance profiles can help scope that guidance to only what an app
> needs.** The hiking trails app doesn't donate person relationships, so **guiding the model on how
> to search for authors and recipients, could be skipped for limited-context models.** To
> selectively enable guidance on search capabilities like **people and dates**, use a
> **`GuidanceProfile`**. **You can even specify the exact list of metadata attributes, that the
> model should consider during a search.** Then set a **dynamic guide level** using the profile, when
> creating `SpotlightSearchTool`."

### 🚨 246:80 — the load-bearing recommendation

> "**On-device models have a more restricted model context size, so it's best to use FOCUSED guidance
> for simpler search capabilities.**"

Quantified by field testing (`spotlight-rag-third-party.md:87-92`) — **this is the single most
useful number in the Spotlight material**:

> "**Guidance level is a token gate.** **`.complete` guidance injects ~13 k tokens of tool
> instructions → instant `contextSizeExceeded` on any 4 k-context model (system or zoo). Ship
> `.focused(.items)` + `format: .compact` for local models.** **`.dynamic(GuidanceProfile)` was
> prompt-sensitive in testing (a model skipped the search and hallucinated) — use deliberately.**"

**[RECONSTRUCTED]** the profile construction the transcript describes:

```swift
let profile = GuidanceProfile(
    textMatch: true,
    similarityMatch: true,
    numericMatch: false,
    dates: true,
    people: false,                       // hiking app donates no person relationships
    contentType: false,
    attributes: [.title, .contentCreationDate, .keywords]   // "the exact list of metadata attributes"
)

let tool = SpotlightSearchTool(configuration: .init(
    sources: [.coreSpotlight(...)],
    guide: SpotlightSearchTool.Guide(level: .dynamic(profile), format: .compact),
    contactResolver: nil,
    customStages: []))
```

(Parameter labels are verified from `spotlight-rag-third-party.md:33`; the **values** are my
reconstruction of the demo's intent.)

## C.10 Customization axis 2 — Reference resolution / `contactResolver` (246:81–85)

> "**Reference resolution** is another way for your app to provide **context that's not directly
> available in the search index.** As an example, if the hiking trails app **did** donate person
> relationships, the person using the app might want to **ask about other participants on the
> trail**. In that case, **the model needs to know who *that person* refers to in a prompt. If the
> app already knows who that person is, use a `contactResolver` to help the tool filter to the right
> set of results.**
>
> "**A `contactResolver` should return any contact information related to the user's identity, that
> can be matched against metadata in the search index.**"

`contactResolver` is a named `Configuration` parameter (verified, `spotlight-rag-third-party.md:22`:
`contactResolver: nil,`). Its exact protocol/closure type is **UNVERIFIED**.

## C.11 Customization axis 3 — Custom pipeline stages (246:86–108)

> 86–90: "your app can take advantage of **custom pipeline stages**, that take document reasoning
> even further. **For really complex requests, the language model might forgo a simple search
> query, in favor of a PIPELINE SEARCH. A pipeline search brings together queries to the index, plus
> computation over a result set, for maximal efficiency.**
>
> I could ask: *how many trails have I hiked this year, and for each month, how many miles have I
> gone on average?* Now, the model could perform a simple search and keep a tally in memory to answer
> the question. **Or, if the result set is likely to be large, `SpotlightSearchTool` allows the model
> to request that Spotlight run a pipeline of search and computation stages.**"
>
> 91–93: "With a pipeline search, the model can **break down this complex query into a set of steps.
> The model might generate a search for completed hikes, along with a COUNTING stage that builds a
> table by month, then a stage that computes an AVERAGE over all counts. Pipeline stages allow the
> tool to perform efficient computation, or transformation, over a search result set on behalf of
> the model.**"
>
> 94–96: "**And your app can participate by registering its own custom stages. Pipeline stages are
> `Generable`, so the model will generate a stage on-demand based on the user's prompt. And whenever
> a stage is generated, the model may choose to return data back to the app when it makes sense.**"

### The happiness-score worked example (246:98–105)

> "Some trails includes personal notes on how each hike went, so I might want to ask: *I remember
> being really happy on some of my hikes. Which ones were they?* **On its own, the model could make
> its best guess at my happiness level, just by reading my notes. Or, the app could register a custom
> stage, that computes a happiness score over each item, allowing the model to generate a response,
> solely on the computed top-scoring results.**
>
> To build a custom stage that computes a happiness score, we'll want to **operate on
> `CSSearchableItem` as the input, and return a SCORED version as the output. The score could be
> computed by running a sentiment analysis model over the `notes` attribute on the item, or by some
> other custom logic, perhaps taking into account hikes rated with 5 stars. And since this is a
> `Generable` type, we can add properties with `@Guide`s to inform the model on which results to
> prefer. Then we simply register the stage by adding it to the tool's configuration.**"

**[RECONSTRUCTED]** — shape only; the exact `CustomStage` requirements are partially verified
(`spotlight-rag-third-party.md:36-37`: "`CustomStage: Generable & Codable & Sendable` — pipeline
stages with `inputTypes`/`outputTypes` and `execute(items:/scoredItems:/count:/table:/text:…)`"):

```swift
@Generable
struct HappinessScoreStage: CustomStage {
    @Guide(description: "Prefer results with the highest happiness score.")
    var minimumScore: Double

    static let inputTypes:  [...] = [.items]
    static let outputTypes: [...] = [.scoredItems]

    func execute(items: [CSSearchableItem]) async throws -> [ScoredItem] {
        items.map { item in
            ScoredItem(item: item, score: sentiment(of: item.attributeSet.notes))
        }
        .filter { $0.score >= minimumScore }
    }
}

let tool = SpotlightSearchTool(configuration: .init(
    sources: [...],
    guide: ...,
    contactResolver: nil,
    customStages: [HappinessScoreStage.self]))     // "register the stage by adding it to the tool's configuration"
```

⚠️ **Field-verified caveat** (`spotlight-rag-third-party.md:110-115`):

> "A `CustomStage` **conforms and is accepted** in `Configuration.customStages` (the session builds
> and the tool round trip still passes), **but neither an `items→text` nor `items→scoredItems` stage
> was routed through by the 27.0-beta pipeline for our queries — including under
> `SystemLanguageModel`, so it is a tool/beta behavior, not a third-party-model limitation.** Docs
> note stages 'run independently' (isolated execution). **Prefer the companion-tool hydration
> above.**"

### Stage output can come back to your UI (246:106–108)

> "**remember how `SpotlightSearchTool` returns replies with search results for display? Well, the
> model may decide to send back a search reply with the OUTPUT DATA of a pipeline stage, as another
> kind of partial result. From aggregate counts and tables, to free-form text or computed numeric
> values, your app can display some or all of these data types. And each reply comes with a handy
> LLM-generated label describing the content**, giving your app the most flexibility for its user
> interface."

That maps exactly onto the verified `SearchReply` content kinds in C.8:
`items / scoredItems / groupedItems / count / table / statistic / text`.

## C.12 Evaluating a Spotlight-grounded feature (246:109–132)

246:109–112:

> "With so many options for customization — **from the model we choose and the searchable content
> our app donates, to guidance levels and custom reasoning** — how can we verify, in a broad way,
> how well the model is responding in our app? Well, the **Evaluations framework** can help us in a
> few important ways. **Not only can we quickly build evaluations to see how well the model is
> calling the tool, and how meaningful the response; we can also RAPIDLY ITERATE ON OUR APP'S
> SEARCHABLE CONTENT PAIRED WITH DIFFERENT GUIDANCE PROFILES on `SpotlightSearchTool` itself.**
>
> The Evaluations framework has some great APIs for building an **end-to-end evaluation suite, from
> large-scale dataset generation, to evaluation runs using custom metrics, and reporting.**"

The chosen metric (246:113–117):

> "we're going to focus on **result coverage** as a way to evaluate the hiking trails conversational
> experience. We want to know, **given a dataset that's indexed in Core Spotlight, how well does the
> model generate responses based on the items we expect it to find.**
>
> We'll start by **defining a dataset that adopts the `ModelSampleProtocol`. Our `TrailRequest`
> already includes the natural language input that a person might ask about trails in our app, the
> output is a language model response and an expectation of the trajectory of the request. We'll
> also be adding a set of UNIQUE IDENTIFIERS of searchable items that we expect the tool to return
> for that prompt.**"

Sample generation (246:118–125):

> "If we have real data to test against, that's great; but if not, we can use **Sample Generation
> APIs** to generate data based on a prompt…
>
> For our evaluations, we can **define a set of hiking trails with the metadata that our app is
> expected to donate to Core Spotlight.** Then we'll build a set of **seed samples**… **Samples can
> be serialized in any `Codable` format, and JSON works well for that purpose.** Our samples include
> **the query and the set of item identifiers we expect to be returned for the search.** We can also
> provide **a sample response that we can use later in a quality comparison with the model's actual
> response.**
>
> Using the Sample Generation APIs **in a command line tool**, I can **expand this seed set to many
> more variations**, to get broad coverage on how people might want to ask about trails."

Trajectory expectation + run (246:126–131):

> "The next step is to **define our evaluation with metrics and trajectory. For our samples, we
> expect the trajectory of a response to include a call to `SpotlightSearchTool` to perform a
> query**, so here's how we might define that expectation.
>
> And here's an overview of an evaluation flow that takes into account **how many expected items
> were included in the final response. In our TEST TARGET, our evaluation will load the trail items
> and samples from our generated datasets. Then, we'll DONATE the trail items to Core Spotlight, and
> configure `SpotlightSearchTool` for this evaluation. Once the evaluation completes its run, we can
> set the expectation for any metric we've included, like RESULT COVERAGE.**"

**[RECONSTRUCTED]** dataset sample type — names verified from the transcript
(`ModelSampleProtocol`, `TrailRequest`), field types inferred:

```swift
struct TrailRequest: ModelSampleProtocol, Codable {
    var input: String                     // "What hikes have I gone on?"
    var output: String                    // expected/sample language model response
    var trajectory: [ExpectedToolCall]    // expects a SpotlightSearchTool call
    var expectedItemIdentifiers: [String] // uniqueIdentifiers the tool should return
}
```

Evaluations cross-references named by the presenter (246:112, 136): sessions on **sample data
generation APIs** and **"creating robust evaluations for an agentic app"** / "the evaluations
agentic deep dive".

## C.13 Closing (246:133–138)

> "It's a big year for Foundation Models… **Download our sample code to see the hiking trails app in
> action.** Try adding your own custom functionality…
>
> And remember, **we're not writing search queries anymore. We're providing the content, and letting
> intelligence do the rest.**"

## C.14 Known real-world failures with `SpotlightSearchTool` (from `forums/`)

Two live threads, both from developers following this exact session:

1. **thread 838904** (`forums/…-foundation-models.txt:27-45`), "Use of `SpotlightSearchTool()`
   returns 'Model Catalog error: Error Domain=`com.apple.UnifiedAssetFramework` Code=5000', although
   model is available" — on **macOS Golden Gate Developer Beta 4**, the exact 5-line snippet from
   the session throws:
   > `"There are no underlying assets (neither atomic instance nor asset roots) for consistency token for asset set com.apple.modelcatalog"`
   ⇒ `SpotlightSearchTool` pulls an asset from the **model catalog** (its own guidance/query model
   asset?), separate from the LLM's own availability check. **Availability `.available` is NOT
   sufficient for `SpotlightSearchTool` to work.**

2. **thread 837226** (`:163-172`), "`SpotlightSearchTool` Not Invoked, Console Error" — the model
   simply **doesn't call the tool**; responses aren't grounded. The developer's workaround attempt:
   ```swift
   let session = LanguageModelSession(tools: [tool]) {
       spotlightSearchInstructions
   }
   let response = try await session.respond(to: prompt, options: GenerationOptions(toolCallingMode: .required))
   ```
   ⇒ `GenerationOptions(toolCallingMode: .required)` is the escape hatch when the model won't call
   the tool on its own — consistent with `.dynamic(GuidanceProfile)` being "prompt-sensitive"
   (C.9). Note this also shows `LanguageModelSession(tools:)` accepts a **trailing instructions
   builder closure**.

Model-choice constraints if running the tool behind a third-party model
(`spotlight-rag-third-party.md:94-107`):
- needs only **`.toolCalling`**; **`.guidedGeneration` is NOT required** (the tool does not constrain
  decoding on the model side) — so it works on GPU-pipelined engines with no logits.
- "**qwen3-0.6b is too small for the rich `SpotlightSearchTool` schema** (loops on `<think>` →
  framework reports 'ended without producing a response'). **Use qwen3-4B or larger.**"
- "**Append `/no_think` to the instructions** to disable qwen3 reasoning — the search→fetch chain
  then completes reliably (5/5 on stock qwen3-4B)."

---

# PART D — Cross-cutting cross-check ledger (transcripts vs local corpus)

| # | Claim | Transcript | Local corroboration | Verdict |
|---|---|---|---|---|
| 1 | One line switches to PCC: `LanguageModelSession(model: PrivateCloudComputeLanguageModel())` | 319:31 | `UsingPrivateCloudCompute.md:43`; `AFMLLMClient.swift:288` | ✅ **agree** |
| 2 | PCC context = 32K, on-device = 4K | 319:44 | docs table `:29-35` agrees; `AppleFoundationModelRegistry.swift:7` `= 32_768` | ✅ PCC agree; ⚠️ on-device see #3 |
| 3 | on-device context 4K | 319:44 | `AFMLLMClient.swift:133-135`: "**iOS 26 reports 4K while the iOS 27 model reports 8K**" | ⚠️ **CONFLICT** — read `contextSize`, don't hardcode |
| 4 | 3 reasoning levels light/moderate/deep, PCC only | 319:49-52 | `UsingPrivateCloudCompute.md:122` names all three + doc links | ✅ agree |
| 5 | reasoning set on `respond` | 319:53 | `contextOptions: ContextOptions(reasoningLevel: .deep)` — `UsingPrivateCloudCompute.md:126-131` | ✅ agree (param label = `contextOptions:`) |
| 6 | `contextSize` on `SystemLanguageModel` and `PrivateCloudComputeLanguageModel` | 319:60 | `AFMLLMClient.swift:140` uses `SystemLanguageModel.default.contextSize`; comment says **Xcode 26.4+ SDK** | ✅ exists; ⚠️ predates 27 SDK |
| 7 | `quotaUsage.isLimitReached` | 319:79 | `UsingPrivateCloudCompute.md:87`; `AppleFoundationModelAvailability.swift:167` | ✅ agree |
| 8 | "belowLimit" nearing case | 319:97 | `case .belowLimit(let info) = model.quotaUsage.status` + `info.isApproachingLimit` — docs `:90-94`, app `:170-173` | ✅ agree |
| 9 | Xcode scheme simulation menu | 319:91-95 | docs `:111-118` | ⚠️ **naming conflict** — see A.10 table |
| 10 | app eligibility "< 2M downloads" | 319:26 | docs say only "certain eligibility requirements" (`:23`) | ⚠️ **transcript-only**; treat as the concrete bar |
| 11 | entitlement | *not spoken* | `com.apple.developer.private-cloud-compute`, managed — docs `:139`, `Origami.md:148`, 4 real `.entitlements` files | ✅ **only in docs/code** |
| 12 | PCC works on watchOS | 319:9 | docs `#available(… watchOS 27.0 …)` `:49`; forums 834652 | ✅ agree |
| 13 | `LanguageModel` / `LanguageModelExecutor` public protocol | 339:53-57 | `fm-provider.md:19-38` (read from `FoundationModels.swiftinterface`); 3 real conformances | ✅ agree, signatures verified |
| 14 | `Configuration` is the executor cache key, `Hashable` | 339:58-66 | `fm-provider.md:190-193`; `ZooExecutor.Configuration` custom `==`/`hash` | ✅ agree |
| 15 | `prewarm` optional / can be a no-op | 339:81-82 | ✅ …**and** it has a **default no-op** that silently swallows near-miss signatures — `fm-provider.md:183-186`, `MLXLanguageModel.swift:901-907`, `ZooExecutor.swift:68-70` | ⚠️ **transcript omits the footgun** |
| 16 | six transcript entry types | 339:98 | `fm-provider.md:41-42` lists `instructions/prompt/toolCalls/toolOutput/response/reasoning` | ✅ agree |
| 17 | event names "textDelta"/"toolCallDelta" | 339:118 | real API is `.appendText(_:tokenCount:)` / `.appendArguments(_:tokenCount:)` — `CoreAILanguageModel.swift:502-543`, `MLXLanguageModel.swift:706-773` | ⚠️ presenter used conceptual names |
| 18 | send metadata → usage **upfront**, then deltas | 339:126-129 | `fm-provider.md:129-132`: doing so **materializes an EMPTY Response entry** on tool-calling turns; Apple's own CoreAI adapter sends usage at the **end** (`CoreAILanguageModel.swift:468`) | 🚨 **CONTRADICTED in beta** |
| 19 | `LanguageModelError` covers "context window overflows, rate limits, refusals" | 339:149 | verified cases: `.unsupportedCapability`, `.unsupportedTranscriptContent`, `.unsupportedGenerationGuide`; `contextSizeExceeded` named in `spotlight-rag-third-party.md:89` | ✅ partial |
| 20 | Anthropic + Google shipping FM provider packages | 339:11 | `fm-provider.md:16-17` repeats it and adds **Hugging Face ships `AnyLanguageModel`** | ✅ agree + extra |
| 21 | FM framework going **open source** | 339:42 | no local corroboration | ⚠️ **UNVERIFIED elsewhere** |
| 22 | `import MLXFoundationModels` | 339 (on-screen) | it is a library in `ml-explore/mlx-swift-lm`; forums 836264 shows devs couldn't find it | ✅ exists, ⚠️ discoverability problem |
| 23 | `SpotlightSearchTool` on iOS/iPadOS/macOS/visionOS | 246:21 | `spotlight-rag-third-party.md` verified macOS 27 beta; no watchOS anywhere | ✅ agree (watchOS excluded) |
| 24 | index stores text "not recoverable by an LLM" | 246:50 | `spotlight-rag-third-party.md:53-64` — even `fetchAttributes:[.contentDescription]` doesn't surface; only identity attrs reach the model | ✅ agree, **worse than described** |
| 25 | `searchableItems(forIdentifiers:)` is "new" for this tool | 246:54-56 | `spotlight-rag-third-party.md:117`: **macOS 15.4+**, new `protectionClass` overload in 27.0, and it is the *index-recovery* path, not the search-time body path | ⚠️ **CONFLICT** |
| 26 | custom pipeline stages work | 246:94-105 | `spotlight-rag-third-party.md:110-115`: stage conforms + is accepted but **was never routed through** on the 27.0 beta, incl. under `SystemLanguageModel` | ⚠️ **beta gap** |
| 27 | use focused guidance for on-device models | 246:80 | `spotlight-rag-third-party.md:89`: `.complete` = **~13k tokens** → instant `contextSizeExceeded` on 4k models | ✅ agree, **quantified** |
| 28 | image input on the on-device model | 319:5, 339:5 | `MultimodalPrompting.md` (whole file): `Attachment(image:)`, `ImageAttachment`, `ImageReference`, formats `CGImage`/`CIImage`/`CVPixelBuffer`/local file URLs; labeled attachments | ✅ agree |

---

# PART E — Consolidated gotchas / footguns

**PCC**
1. Managed entitlement `com.apple.developer.private-cloud-compute` + application; transcript adds
   "**apps with less than 2M downloads**".
2. PCC requires **network**; docs say **retry on the on-device model** when the network fails.
3. `availability` must be checked; cases `.available`, `.unavailable(.deviceNotEligible)`,
   `.unavailable(.systemNotReady)`, `.unavailable(other)` + `@unknown default`.
4. Reasoning tokens **count against the 32K context**.
5. Quota is tied to the **user's iCloud account**, not your app. **Never show an alert** for quota —
   persistent, non-dismissible in-place UI + a `limitIncreaseSuggestion.show()` button.
6. `resetDate` is **empty** when unknown or when the user is well below their limit.
7. Quota-limit-reached is **not** rate limiting: waiting minutes doesn't help; it's wait-for-refresh
   or upgrade.
8. Do **not** hardcode 4096 for the on-device context; call `contextSize` (iOS 27 reportedly 8K).
9. Xcode scheme option names differ between the talk and the docs — trust the docs' "Run → Options →
   Simulated Apple Foundation Models Availability".

**Provider protocol**
10. 🚨 `prewarm(model:transcript:)` must match **exactly** (concrete `Transcript`); a default no-op
    silently wins otherwise. Apple's own CoreAI adapter has this bug.
11. 🚨 The talk's "metadata → usage upfront → deltas" order materializes an **empty Response
    transcript entry** on tool-calling turns in the 27.0 beta. Send usage at end-of-turn attached to
    the entry kind the turn produced.
12. 🚨 `Response.Action.updateUsage(input:output:metadata:)` exists in the beta `.swiftinterface` but
    **not** in the shipping dylib → **process abort at image load** under chained fixups, or SIGSEGV
    at 0x0. Don't reference the 3-param overload.
13. `request.enabledToolDefinitions` is the property name; `enabledTools` is only the init label.
14. `Configuration` is the executor cache key — key it on model identity + anything that changes
    behavior; it must be `Hashable` even if it wraps non-Hashable engine handles (implement `==`/`hash`).
15. Declaring `.reasoning` is **routing-relevant**: the framework only forwards `reasoningLevel` to
    executors declaring it, and auto-rejects otherwise before `respond` runs.
16. Don't declare `.guidedGeneration` without logits access — GPU-pipelined engines sample on-GPU
    and cannot honor a schema. Throw `.unsupportedCapability` instead.
17. Breaking out of a token stream does **not** stop a pipelined engine; over-generated post-EOS
    tokens land in the KV cache and break your transcript-diff prefix match.
18. Small `maximumResponseTokens` + a thinking model = **no response at all** ("ended without
    producing a response") when the cap cuts generation mid-`<think>`.
19. Tool-call dialects are per-model-family and **do not transfer** — the training prior beats
    in-context instructions.
20. Server model packages: no `init(apiKey: String)`; use token provider / sign-in + Keychain + App Attest.
21. Weights cached in a process-global store (MLX pattern) opt out of the automatic
    session-deallocation teardown the talk promises — you must expose `evict()`.

**Spotlight**
22. 🚨 The tool's output carries **identity metadata only** — the model sees titles, not bodies, and
    will hallucinate content. Add a companion `Tool` that hydrates by identifier.
23. `.complete` guidance ≈ **13k tokens** → immediate `contextSizeExceeded` on 4k models. Use
    `.focused(.items)` + `format: .compact` for on-device.
24. `.dynamic(GuidanceProfile)` is prompt-sensitive; a model may skip the search entirely.
25. The model may call the tool **multiple times per response** — key your UI refresh on `queryToken`.
26. `CustomStage`s were **not routed through** on the 27.0 beta even under `SystemLanguageModel`.
27. `SpotlightSearchTool()` can fail with `com.apple.UnifiedAssetFramework Code=5000` /
    `com.apple.modelcatalog` even when the LLM reports available.
28. `GenerationOptions(toolCallingMode: .required)` is the escape hatch when the model won't call
    the tool.
29. Tiny models (≤0.6B) can't handle the tool's schema. Use ≥4B, or append `/no_think` for qwen3.
30. `SpotlightSearchTool` only materializes when a file imports **both** `CoreSpotlight` **and**
    `FoundationModels` (cross-import overlay `_CoreSpotlight_FoundationModels`).

---

# Source inventory (everything I actually opened this session)

**Transcripts (read in full, Read tool):**
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-319.txt` (109 lines)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-339.txt` (213 lines)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-246.txt` (138 lines)

**Written Apple documentation mirrors (local):**
- `…/repos/noemaai-labs__noema-ios/DocumentationforAPIs&SDKs/AppleFoundationModels/UsingPrivateCloudCompute.md` (144 lines, read in full) — source URL
  `https://developer.apple.com/documentation/foundationmodels/adding-server-side-intelligence-with-private-cloud-compute`, timestamp `2026-06-08T20:15:43.771Z`
- `…/AppleFoundationModels/Overview.md` (lines 1–120)
- `…/AppleFoundationModels/MultimodalPrompting.md` (lines 1–80)
- `…/AppleFoundationModels/Origami.md` (lines 135–165)

**Real conforming implementations (local repos):**
- `…/repos/apple__coreai-models/swift/Sources/CoreAILanguageModels/LanguageModel/CoreAILanguageModel.swift` (lines 1–140, 240–300, 410–480, 495–600)
- `…/repos/ml-explore__mlx-swift-lm/Libraries/MLXFoundationModels/MLXLanguageModel.swift` (lines 1–1324 of 2104)
- `…/repos/john-rocky__coreai-model-zoo/swift/Sources/ZooFMProvider/ZooExecutor.swift` (lines 1–160)

**Field-verification knowledge notes (local repos):**
- `…/repos/john-rocky__coreai-model-zoo/knowledge/fm-provider.md` (222 lines, read in full) — explicitly sourced to WWDC26 339 + the macOS 27 beta `FoundationModels.swiftinterface`
- `…/repos/john-rocky__coreai-model-zoo/knowledge/spotlight-rag-third-party.md` (119 lines, read in full) — explicitly sourced to WWDC26 246, verified 2026-06-13 macOS 27 beta / M4 Max

**Shipping app code (local repo):**
- `…/repos/noemaai-labs__noema-ios/Noema/AFMLLMClient.swift` (lines 80–160, 280–300, 385–430)
- `…/repos/noemaai-labs__noema-ios/Noema/AppleFoundationModelAvailability.swift` (lines 150–225)
- `…/repos/noemaai-labs__noema-ios/Noema/AppleFoundationModelRegistry.swift` (lines 4–10, 24, 77, 90)
- `…/repos/noemaai-labs__noema-ios/Noema/{Noema,NoemaDirect,NoemaVisionOS,RelayServer}.entitlements` (grep)

**Forums (local):**
- `…/forums/machine-learning-and-ai-foundation-models.txt` — threads **838904** (SpotlightSearchTool
  model-catalog error), **837226** (tool not invoked), **836264** (missing MLXFoundationModels),
  **834749** (accessing PCC), **834652** (watchOS 27 PCC), **838444** (`ChatCompletionsLanguageModel`
  in `apple/foundation-models-utilities`), **836673** (iOS 27 refusal regression), **835987**
  (watchOS 27 `.swiftinterface` CoreImage dependency error), **836760** (FM tied to Siri AI on macOS beta 2)

**Checked but NOT relevant to this theme (no FM-protocol content):**
- `…/docs/*.md` (7 files: Core AI compilation/specialization/caching, Speech, "Run AI models in your
  app on Apple silicon") — grepped for `LanguageModel*`, `PrivateCloudCompute*`, `SpotlightSearchTool`,
  `quotaUsage`, `contextSize`: **zero hits**. These docs cover Core AI's own APIs, not the FM bridge.

---

# Open questions / UNVERIFIED

1. **Exact `CustomSegment` protocol name and requirements.** 339:184 says "define a type that
   conforms to custom segment" and that it "must be `PromptRepresentable`". No local implementation
   exists. The channel action for emitting one ("custom segment update") is also unverified.
2. **Whether `ContextOptions` carries the response schema.** 339:109 says ContextOptions control
   "what goes into the prompt, like the reasoning level … **or a response schema**", but all three
   real executors read `request.schema`. Are both present? Is one a convenience?
3. **`LanguageModelExecutorGenerationRequest.contextOptions` full member list.** Only
   `reasoningLevel` is exercised locally.
4. **Server-side tools API shape.** 339:194 — "named, typed values on your model". No protocol name,
   no example, no local implementation. How does the executor read them off the model? Is there a
   `ServerSideTool` protocol?
5. **The FM framework open-source repo.** 339:42 announces it; no URL, no local repo, no docs
   mention. Is it `apple/swift-foundation-models`? Related: `apple/foundation-models-utilities`
   exists (forums 838444/`:256-260`) and ships a `ChatCompletionsLanguageModel` with an
   OpenAI-compatible `buildURLRequest` — **is that the reference third-party `LanguageModel`
   implementation?** Worth a dedicated dig.
6. **`GuidanceProfile` parameter value types.** Labels verified
   (`textMatch:similarityMatch:numericMatch:dates:people:contentType:attributes:`) but not whether
   they are `Bool`, an option set, or per-capability enums; `attributes:` is presumably
   `[CSSearchableItemAttributeSet` key paths / `String]`.
7. **`contactResolver` type.** A `Configuration` label; protocol/closure signature unknown.
8. **`SearchReply` exact shape** — is `content` an enum with `.items([CSSearchableItem])` etc.? Is
   `status` an enum with a terminal case? Is `queryToken` `UUID`/`String`?
9. **`CustomStage.inputTypes`/`outputTypes` element type** — some `StageDataType` enum, presumably.
10. **Does PCC accept image attachments?** 319:75 says the demo feeds "the text **and images**" of a
    markdown file into a `LanguageModelSession` backed by PCC. No doc corroboration; no statement
    about separate image limits or costs.
11. **watchOS PCC and Apple Intelligence enablement** — forums 834652 asks whether watchOS 27 has a
    separate Apple Intelligence setting, and what happens with an AI-capable Watch paired to a
    non-AI-capable iPhone. Unanswered.
12. **Exact `LanguageModelError` case list.** Talk names "context window overflows, rate limits,
    refusals, and more"; I verified only four cases by name. Need the full enum.
13. **`PrivateCloudComputeLanguageModel.Error`** appears to be a *nested* error type separate from
    `LanguageModelError` (doc path `privatecloudcomputelanguagemodel/error/quotalimitreached(_:)`).
    Relationship between the two is unclear.
14. **Does the on-device `SystemLanguageModel` really report 8K on iOS 27?** One shipping-app comment
    says so against Apple's own 4K slide + docs table. Needs device confirmation.
15. **"indexed entities for Apple Intelligence"** (246:24) as an alternative to Core Spotlight
    donations — is that App Intents `@AssistantEntity` indexing? Does `SpotlightSearchTool` search it
    via the same `.coreSpotlight` source?
16. **Session 339's "Dynamic Profiles" claim** (339:23) — that third-party models get Dynamic
    Profiles for free. Not verified against any `DynamicProfile` + custom-`LanguageModel` example.
17. **Apple's official session titles/numbers** for the cross-referenced talks ("Meet the Evaluations
    framework", "What's new in the Foundation Models framework" = likely 241, "Build agentic app
    experiences with the Foundation Models framework", "Debug and profile agentic app experiences
    with Instruments", "Secure your apps with App Attest", "Supporting semantic search with Core
    Spotlight", "Deep dive into the Foundation Models framework", "Creating Swift Packages").
    `fm-provider.md:218-219` maps 339 → "Bring an LLM provider…" and 241 → "What's new in the
    Foundation Models framework". Others unmapped.
