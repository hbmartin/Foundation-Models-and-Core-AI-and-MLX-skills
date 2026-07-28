# Foundation Models — Core Framework: Transcript Deep-Read Notes (theme `fm-core`)

**Agent scope:** deep-read of three Apple transcripts covering the *core* Foundation Models framework —
sessions, prompting, `@Generable`/`@Guide`, snapshot streaming, `Tool`, instructions vs. prompts,
availability, context window, performance, and everything NEW in the 2026 / iOS 27 release.

**Sources read IN FULL this session** (all under `/Volumes/ExtStor/FM and MLX and CoreAI/`):

| File | Lines | Title / speaker |
|---|---|---|
| `transcripts/wwdc2026-241.txt` | 140 | **What's new in Foundation Models** — Erik & Zhen |
| `transcripts/wwdc2026-334.txt` | 171 | **Foundation Models on macOS** (`fm` CLI + Python SDK) — Eric Gourlaouen, FM Framework team |
| `transcripts/meet-with-apple-205.txt` | 1013 | **Foundation Models Framework Code-Along** — Shashank, Technology Evangelist |

**Citation convention below:** `[241:L31]` = `transcripts/wwdc2026-241.txt` line 31. `[205:L620]` = the code-along.
`[334:L88]` = the macOS session.

**Reconstruction convention:** these are spoken-word transcripts. Code shown on screen is *described*,
not dictated. Every code block below is tagged:
- **`VERBATIM-ISH`** — the presenter literally read the identifiers/strings aloud; identifier spelling
  is normalized from spoken form (e.g. "session dot stream response" → `session.streamResponse`).
- **`RECONSTRUCTED`** — shape inferred from the narration; signature/parameter order/labels may differ.
- **`UNVERIFIED`** — I could not confirm this from any source in this session.

---

# PART 0 — TL;DR: what is new in the 2026 / iOS 27 release vs. the 2025 / iOS 26 release

This is the single highest-value delta table. Everything here is sourced from `241` and `334`.
The code-along (`205`) is the **iOS 26 / Xcode 26 / macOS Tahoe baseline** — it explicitly targets
"macOS Tahoe and Xcode 26" `[205:L55]` — so it doubles as the "before" column.

| Area | iOS 26 (2025 baseline, per `205`) | iOS 27 / macOS 27 (2026, per `241`/`334`) |
|---|---|---|
| On-device model | original SLM | **"a new on-device model, rebuilt from the ground up, and better across the board… more intelligent; better at logic and tool calling"** `[241:L12-13]` |
| Multimodal input | text only | **Image attachments in prompts** — on-device model gains Vision `[241:L20-27]` |
| Server model | none | **`PrivateCloudComputeLanguageModel`** — 32,000-token context, reasoning `[241:L29-31]` |
| Reasoning | none | **`reasoningLevel`** on a new **`contextOptions`** argument `[241:L35-37]` |
| Model pluggability | `SystemLanguageModel` only | **`LanguageModel` protocol** — any local or server model can back a `LanguageModelSession` `[241:L45]` |
| Open-source models | — | **`CoreAILanguageModel`** and **`MLXLanguageModel`** open-sourced `[241:L47]` |
| 3rd-party models | — | **Anthropic and Google publishing Swift packages** `[241:L48]` |
| Token accounting | — | **`usage` property on sessions and responses**; cached-input tokens; reasoning tokens `[241:L55-56]` |
| Context introspection | — | context-size inspection + token counting for instructions/prompts/transcripts, **shipped in iOS 26.4** `[241:L14-16]` |
| Built-in tools | none (bring your own) | **`BarcodeReaderTool`**, **`OCRTool`** (Vision-backed), **Spotlight search tool** for local RAG `[241:L59-66]` |
| Agentic primitives | manual multi-session juggling | **Dynamic profiles** — `DynamicProfile` protocol, `Profile`, modifiers `[241:L68-104]` |
| Quality measurement | ad hoc | **Evaluations framework** (Swift; Xcode 27) `[241:L106]`, `[334:L120-121]` |
| CLI | none | **`fm` CLI, pre-installed with macOS 27** `[241:L111-121]`, `[334:L15]` |
| Python | none | **Foundation Models SDK for Python** `[241:L122-126]`, `[334:L20]` |
| Distribution | closed framework | **Framework core going OPEN SOURCE**, plus **Foundation Models framework utilities** package `[241:L5]`, `[241:L133-135]` |
| Platforms | iOS/macOS/iPadOS/visionOS | **+ watchOS 27** (via PCC) `[241:L40-41]`; **+ Linux** (via open source) `[241:L134]` |
| Guardrails | — | false-positive reduction in **iOS 26.4**, "continuing to make even more improvements in iOS 27" `[241:L17-19]` |

---

# PART 1 — `wwdc2026-241.txt` "What's new in Foundation Models"

Presenters: **Erik** and **Zhen** `[241:L1]`.

## 1.1 Framing quotes

> "Last year we introduced the Foundation Models framework with features like **guided generation,
> snapshot streaming, and the powerful tool protocol**." `[241:L1]`

This is the canonical three-feature summary of the 2025 release. Note the exact term **"snapshot
streaming"** — that is Apple's name for the `PartiallyGenerated` streaming model (see Part 3, Ch. 4).

> "**Our 2027 release** is all about integrations into and beyond the OS, a wider variety of models,
> and new primitives for building agentic experiences." `[241:L3]`

⚠️ **ODDITY / flag for guide writers:** the transcript literally says *"Our 2027 release"* even
though every OS reference in the same session is **iOS 27 / macOS 27 / watchOS 27** and the session
is WWDC26. Either (a) Apple internally calls the OS-27 cycle "the 2027 release", or (b) transcription
artifact. **Do not repeat "2027 release" in a guide without a caveat.** Use "iOS 27 / macOS 27".

Session agenda as stated `[241:L7-11]`:
1. New models, new modalities, new tools (Erik)
2. New APIs to exploit them (Zhen)
3. Dynamic profiles — "our new primitive for creating agentic experiences"
4. Evaluations framework and its tight integration with Foundation Models
5. "Mac-specific productivity tools"

## 1.2 OPEN SOURCE — the headline

> "The Foundation Models framework, **including many of the brand new APIs that we're announcing
> today, is going open source**! And doing it in style! In addition to the core framework, we're also
> releasing a new package, **Foundation Models framework utilities**, that will be **updated between
> OS releases** to give you access to **emerging and experimental building blocks**." `[241:L5]`

> "And during the course of this session, you'll be hearing about **multiple other packages** all
> joining the Foundation Models framework ecosystem." `[241:L6]`

Later, restated `[241:L133-135]`:

> "In addition to the utilities package, **the core of the FoundationModels framework will also be
> open source.** Open sourcing the Foundation Models framework makes it a great solution for
> interacting with LLMs everywhere Swift runs, **including Linux servers**. Together with other model
> providers like Anthropic and Google, alongside CoreAI and MLX integrations, **you'll be able to run
> any model, anywhere**."

**Key architectural takeaway:** the framework is being repositioned from "an Apple-Intelligence API"
to "a **portable Swift LLM client abstraction**" — Linux-capable, provider-agnostic.

### Foundation Models framework utilities — stated contents `[241:L128-132]`

> "Utilities contains a collection of building blocks to help you explore emerging practices in
> working with LLMs. It provides:
> - **profile modifiers for transcript management**,
> - **a skill API for procedural knowledge loading**, and
> - **a language model that can interface with servers using the Chat Completions standard.**
>
> These are just the starting points. Tools and trends evolve, and the Foundation Models framework
> utilities is there to grow with you."

**Cadence gotcha:** utilities ships **out of band with the OS** ("updated between OS releases") and is
explicitly labelled "**emerging and experimental**". Treat its API surface as unstable relative to
the in-OS `FoundationModels` framework.

## 1.3 New on-device model

`[241:L12-19]`:
- "a new on-device model, **rebuilt from the ground up**, and better across the board."
- "It's more intelligent; **better at logic and tool calling**."
- **"In iOS 26.4, we released new APIs for inspecting the model's context size and counting the
  tokens in instructions, prompts, and transcripts."**
- **"You'll want to use these going forward to adapt your app to the hardware it's running on."**
  → strongly implies **context size varies by device/hardware**, and apps are expected to branch on it.
- Guardrails: "You may have noticed adjustments in **iOS 26.4 to reduce the number of false
  positives**, and we're continuing to make even more improvements in iOS 27."

**Version gate to record:** context-size + token-counting APIs = **iOS 26.4**, not iOS 27.

## 1.4 Vision / image attachments on the on-device model

`[241:L20-27]`:

> "In addition the on-device model is also gaining **Vision capabilities**, which unlocks entire new
> categories of applications. **The API is simple, a natural extension of the existing prompt
> builders.** Here we've created a session, and we want to ask about the photo of the origami on the
> right. **Simply insert an image attachment into your prompt, together with text.** Now, the model
> can answer questions about the image."

**Accepted source types for image attachments** (exact list read aloud, `[241:L25]`):
- `UIImage`
- `NSImage`
- `CGImage`
- "Core Image types" (i.e. `CIImage` — UNVERIFIED exact type name)
- "CoreVideo Pixel Buffers" (`CVPixelBuffer`)
- **file URLs** (`URL`)

Sizing rules `[241:L26-27]`:
> "The model supports **images in any size and aspect ratio, so you don't need to crop or pad to any
> particular shape**. Arbitrary image sizes are allowed, but bear in mind that **larger images will
> consume more tokens and incur more latency**."

**RECONSTRUCTED** call shape (the exact attachment type name is NOT stated in this transcript):

```swift
// RECONSTRUCTED — the transcript says "insert an image attachment into your prompt,
// together with text" via "the existing prompt builders". Exact type name unverified.
let session = LanguageModelSession()

let response = try await session.respond(to: Prompt {
    "What kind of origami is this?"
    /* image attachment value, constructed from UIImage/NSImage/CGImage/CIImage/CVPixelBuffer/URL */
})
```

⚠️ **UNVERIFIED:** I did not find the concrete attachment type name (e.g. `ImageAttachment`,
`Prompt.Image`) in any source I read this session. Another agent covering "What's new in image
understanding" should pin this down.

**Related forum data point** (`forums/machine-learning-and-ai-foundation-models.txt`, thread 838613,
"Foundation Models, image input and locating things within an image", 20 Jul 2026): a developer
reports image identification "working well" but that bounding-box / coordinate localization is
unreliable — the model "consistently lists the items in the image and gives me bounding boxes" but
the boxes are the problem. **Gotcha: don't rely on FM image input for spatial localization; use
Vision.**

## 1.5 `PrivateCloudComputeLanguageModel`

`[241:L29-43]`. Facts:
- "**the very same one that powers many of the Apple Intelligence features you know and love**."
- "**a much bigger model** than the on-device models"
- **32,000 token context window** `[241:L31]`
- "comes with a powerful new capability, **reasoning**."
- > "Reasoning models are trained to spend time carefully thinking through their answers before
  > providing a response, which results in significantly better outcomes." `[241:L32]`

Usage `[241:L33-37]`:
> "Just **create an instance of the model and use it to initialize your language model session**.
> When prompting the session, I can now specify a **reasoning level** on the new **`contextOptions`**
> argument. **`reasoningLevel` controls how much the model is allowed think before responding. Deep
> reasoning produces better responses in exchange for additional compute.**"

**RECONSTRUCTED**:

```swift
// RECONSTRUCTED from [241:L33-37] + forum-confirmed initializer
let session = LanguageModelSession(model: PrivateCloudComputeLanguageModel())

let response = try await session.respond(
    to: prompt,
    contextOptions: ContextOptions(reasoningLevel: .deep)   // exact type name UNVERIFIED
)
```

✅ **Cross-check (forums):** thread 834749 "Accessing Private Cloud Compute" (15 Jun 2026) contains
literally:
```swift
let session = LanguageModelSession(
model: PrivateCloudComputeLanguageModel()
)
```
This **confirms the `model:` initializer label and the exact type name `PrivateCloudComputeLanguageModel`.**

⚠️ `contextOptions` type name and `reasoningLevel` case names (`.deep`? `.high`? `.minimal`?) are
**UNVERIFIED**. The only case Erik names is "**Deep reasoning**" `[241:L37]` and Zhen says "a
`reasoningLevel` modifier to ask the model think thoroughly" `[241:L94]`.

### PCC privacy & economics `[241:L38-43]`

> "you don't have to worry about **account setup**, you don't have to deal with **authentication**,
> and you don't have to **store API keys**, it's all completely seamless!"

> "**No prompts are ever stored**, and we make it possible for **independent researchers to verify
> these claims**."

> "**PCC is available with no cloud API costs to developers who have less than 2 million first time
> downloads.** Your users will have access to PCC **every day** and **if they are subscribed to
> iCloud+, their limit will be even higher!**" `[241:L42]`

> "…including **the entitlement you'll need to use it**, make sure to tune in to our video about
> building with Private Cloud Compute." `[241:L43]` → that is `wwdc2026-319.txt`.

**Two quota layers to teach:**
1. **Developer eligibility gate** — < 2M *first-time downloads* → no cloud API cost.
2. **Per-user daily limit** — raised for iCloud+ subscribers.

✅ **Forum corroboration + friction:** thread 835897 "I did well on iOS a decade ago. So - no
foundation models for me?" (24 Jun 2026): *"I had 180k downloaded units in the last year - but I'm
excluded from foundation models because I did well before 2015… **Lifetime downloads**"* — i.e. the
2M is measured **lifetime/cumulative**, not per-year, and developers are hitting it.

✅ **Forum corroboration on quota opacity:** thread 835974 "More Detailed Quota Usage for PCC"
(24 Jun 2026): *"You can tell if you've reached your quota or are below it. If you are below your
quota, you can tell if you're approaching the limit, but what does this actually mean? Am I over 50%,
90%, 99%?"* → **the quota API exposes coarse states (reached / below / approaching), not numbers.**
That is a concrete gotcha worth a guide callout.

### watchOS

> "And to top it all off, **Private Cloud Compute makes it possible for us to bring the Foundation
> Models framework to watchOS**. Starting in **watchOS 27**, you can wear your most powerful
> intelligence features right on your wrist." `[241:L40-41]`

**Implication:** on watchOS the framework is (at least primarily) a **PCC-only** surface — the
on-device model is not described as running on the watch.

⚠️ **Open question surfaced by forums** (thread 834652): if a user has an Apple Watch Series 11
(AI-capable) paired with an iPhone 15 (not AI-capable), can they use FM/PCC? And is there a separate
Apple Intelligence toggle in watchOS 27? **Unanswered in the material I read.**

⚠️ **Known watchOS 27 beta 2 build bug** (forums thread 835987): importing `FoundationModels` on
watchOS 27 beta 2 fails with
```
.../WatchOS27.0.sdk/System/Library/Frameworks/FoundationModels.framework/Modules/FoundationModels.swiftmodule/arm64e-apple-watchos.swiftinterface:6:15
Unable to resolve module dependency: 'CoreImage'
```
(Presumably a fallout of the new image-attachment API pulling in CoreImage on a platform without it.)

## 1.6 The `LanguageModel` protocol / model abstraction layer

`[241:L44-47]`:

> "we're **opening up our model abstraction layer** to make it possible for **nearly any language
> model to be used with the Foundation Model's framework**. The abstraction layer is built around a
> **new `LanguageModel` protocol** that allows both local and servers models to **back a
> `LanguageModelSession`**. Existing models like **`SystemLanguageModel`** and
> **`PrivateCloudComputeLanguageModel`** already conform to this protocol."

> "And, we're open sourcing two additional implementations: **`CoreAILanguageModel`** and
> **`MLXLanguageModel`**, for running a myriad of local models on the Apple Neural Engine [and] your
> Mac's GPU." `[241:L47]`
> *(transcript reads "on the Apple Neural Engine in your Mac's GPU" — almost certainly "and".)*

Third-party `[241:L48-49]`:
> "**Anthropic, and Google are both publishing Swift packages** to provide you with access to their
> latest and greatest models! The model abstraction layer makes using third party models simple.
> I'll just **import a language model package using Swift Package Manager, initialize the model that
> I want to use, and pass it when creating my session.**"

> "**Everything downstream stays the same.**" `[241:L50]` ← this is the whole value proposition.

**RECONSTRUCTED**:

```swift
// RECONSTRUCTED from [241:L48-50]
import FoundationModels
import SomeVendorLanguageModelPackage   // added via Swift Package Manager

let model = VendorModel(/* … */)
let session = LanguageModelSession(model: model)

// downstream is identical: respond(to:), streamResponse(to:generating:), tools, @Generable …
```

### Third-party security guidance (verbatim, `[241:L51-53]`)

> "Bear in mind that if you use third party server models, **you'll probably have to deal with both
> authentication and billing**. **Remember, never store private keys in your app binary. Always fetch
> access tokens with a secure mechanism like OAuth, and store them securely using KeyChain.**"

### `usage` — token accounting `[241:L54-56]`

> "As a developer, you'll typically be **billed per-token** when using 3rd party models, so we've made
> it easy to keep track of your usage. **Sessions and responses now have a `usage` property that tells
> you precisely how many tokens were used. You can also check how many of the input tokens were read
> from cache, and how many of the response tokens were used for reasoning.**"

**RECONSTRUCTED shape** — three distinct facets confirmed by the narration:

```swift
// RECONSTRUCTED — property names beyond `usage` are UNVERIFIED
session.usage       // cumulative for the session
response.usage      // for a single response

// facets described aloud:
//   - total input tokens
//   - total output/response tokens
//   - how many INPUT tokens were read from CACHE
//   - how many RESPONSE tokens were REASONING tokens
```

Deep dive pointer: **"Bring an LLM provider to the Foundation Models framework"** `[241:L57]` →
`transcripts/wwdc2026-339.txt`.

## 1.7 System tools (built-in `Tool` implementations)

`[241:L58-66]`:

> "we're introducing several **built-in tools that supercharge your `LanguageModelSession`s with
> system provided functionality**. FoundationModels now contains **two native tools backed by the
> Vision framework's powerful capabilities**."

- **`BarcodeReaderTool`** — "allows the model read information from barcodes"
- **`OCRTool`** — "allows the model to extract structured text from images"
- > "Both enhance a model's ability to reason about visual information **in ways it can't natively**."
- Deep dive: **"What's new in image understanding"** `[241:L62]`

- **Spotlight search tool** `[241:L63-66]`:
  > "we're also introducing a **search tool powered by Spotlight** for implementing **fully local
  > Retrieval-Augmented Generation**. **This has been one of your most most requested features.**
  > Retrieval-Augmented Generation, or RAG, is a technique that gives the model access to **up-to-date
  > personal or domain knowledge** by leveraging a **Spotlight index and specially processed queries**."
  - Deep dive: **"LLM search using Core Spotlight"** → `transcripts/wwdc2026-246.txt`

✅ **Exact name confirmed by forums, NOT by this transcript:** the tool is **`SpotlightSearchTool`**.
Thread 838904 contains verbatim:

```swift
import CoreSpotlight
import FoundationModels

let tool = SpotlightSearchTool()

let session = LanguageModelSession(tools: [tool])

let response = try await session.respond(to: "What hikes have I gone on?")
```

⚠️ **Known bug (macOS "Golden Gate" Developer Beta 4):** the above returns
```
Model Catalog error: Error Domain=com.apple.UnifiedAssetFramework Code=5000
"There are no underlying assets (neither atomic instance nor asset roots) for consistency token
for asset set com.apple.modelcatalog"
```
even when the model reports available.

⚠️ **Second known issue** (thread 837226, 07 Jul 2026): `SpotlightSearchTool` silently not invoked.
That thread also shows a **NEW `GenerationOptions` parameter not mentioned in any of my three
transcripts**:

```swift
let session = LanguageModelSession(tools: [tool]) {
    spotlightSearchInstructions
}
let response = try await session.respond(to: prompt, options: GenerationOptions(toolCallingMode: .required))
```

→ **`GenerationOptions(toolCallingMode: .required)`** is a 2026-era addition. Record it.
Note also the trailing-closure form `LanguageModelSession(tools:) { instructions }` — an
`@InstructionsBuilder` trailing closure on the initializer.

## 1.8 Dynamic profiles (Zhen)

`[241:L68-104]`. This is the flagship new **agentic** primitive.

### Motivating demo `[241:L69-74]`
Crafts app. Journal entry with origami photos.
1. Session starts in **craft analysis mode** — instructions tell the model to analyze the images and
   record what it finds; identifies **craft type, colors, materials**; **saves them back to the
   journal through a tool call**.
2. App switches to **brainstorming mode** using **PCC's reasoning capability**; takes everything it
   just learned and suggests creative origami projects.

### The problem statement (verbatim, `[241:L75-79]`)

> "To implement this feature, I'd start by creating a `LanguageModelSession`. Then I'll add more
> sessions, each with its own models, instructions, and tools. **But what if I want the model to
> autonomously switch modes? Things start to get hairy.** Managing context and orchestrating an
> agentic system like this can involve **a lot of boilerplates**. That's why Foundation Models is
> introducing **a new declarative API, dynamic profiles**, so you can **focus on what matters in the
> context, and worry less about imperative controls, all within a single `LanguageModelSession`**."

### API shape `[241:L80-83]`

> "To create a simple dynamic profile, I can **declare a struct, and conform it to the
> `DynamicProfile` protocol with a `body` property that contains a `Profile`**. Language model
> sessions now can be **initialized with a `DynamicProfile`**. I can specify **the instructions and
> tools, that should be present in the context, at that very moment**. **This is the simplest form of
> a `DynamicProfile`, a data structure made up of instructions, and tools.**"

**RECONSTRUCTED** — this is a SwiftUI-`View`-like DSL (`body` + result builder + modifiers):

```swift
// RECONSTRUCTED from [241:L80-98]. Shape is clearly SwiftUI-analogous.
struct CraftsProfile: DynamicProfile {
    var mode: Mode                       // from an @Observable object in the app

    var body: some Profile {
        switch mode {
        case .craftAnalysis:
            Profile {
                Instructions {
                    "Analyze the images and record what you find: craft type, colors, materials."
                }
            }
            .tools([SaveToJournalTool(), SwitchToBrainstormTool()])

        case .brainstorm:
            Profile {
                Instructions { "Suggest creative origami projects based on what you learned." }
            }
            .model(PrivateCloudComputeLanguageModel())     // "a model modifier to specify PCC"
            .reasoningLevel(.deep)                         // "a reasoningLevel modifier"
        }
    }
}

let session = LanguageModelSession(profile: CraftsProfile(mode: appState.mode))
```

Narration backing each piece:
- "My app has an **observable object that stores a `mode` variable, so I can switch on it**." `[241:L85]`
- "In the different branches, the `LanguageModelSession` should have **different instructions and
  tools**." `[241:L86]`
- "**I can even give the model a tool, to intelligently switch to the context for brainstorm mode.**"
  `[241:L87]` ← *the mode switch itself is exposed to the model as a tool.* Key design idiom.
- "Sometimes it's not enough to just manage the context, you may also want **different models and
  configurations for different tasks, while still maintaining the conversation history**." `[241:L88]`
- "For quick tasks like analyzing a craft, `SystemLanguageModel` is probably enough. Now, if I want to
  switch to brainstorming, I can also specify **Private Cloud Compute, configured with deep
  reasoning**." `[241:L91-92]`
- "To describe those configurations, I can use **modifiers**. **A model modifier to specify PCC**, and
  **a `reasoningLevel` modifier to ask the model think thoroughly**." `[241:L93-94]`

### The single most important semantic rule (verbatim, `[241:L97-98]`)

> "**The important thing to understand is that a `DynamicProfile` resolves to a single active
> `Profile` at any given time. You use conditionals to pick which `Profile` is active, and the
> framework handles the transition for you.**"

### What survives a profile switch `[241:L100-101]`

> "As I select the idea, **the model switches to Private Cloud Compute. It still has the full context
> from the analysis**, but generating creative project ideas benefits from the larger model's
> capabilities, like better tool calling, and broader world knowledge."

→ **Conversation history / transcript is preserved across a model swap.** That is the headline
capability: one session, mutable model.

### Guidance (verbatim, `[241:L103]`)

> "When using this API, consider **privacy boundaries, model capabilities, and cost**."

**Privacy boundary** is the loaded one: switching a profile from `SystemLanguageModel` → PCC →
third-party server model means **the accumulated on-device transcript gets shipped to the new
backend**. Guides must call this out.

Deep dive: **"Build agentic app experiences with Foundation Models framework"** `[241:L104]` →
`transcripts/wwdc2026-242.txt`.

✅ **Cross-check against `wwdc2026-242.txt`** (grep only, not my assignment — for another agent):
- L12: "we're announcing a new package; **Foundation Models framework utilities**."
- L13: "Utilities is an **open source Swift package** that houses components helpful for building
  agentic experiences."
- L86: "We've made a number of useful **modifiers** available in the new Foundation Models framework
  utilities package." ← **modifiers live partly in `utilities`, not only in the OS framework.**
- L137: "the Foundation Models framework utilities package houses a **`Skills` type**, which you may
  be familiar with as a popular pattern for **procedural context loading**."

## 1.9 Evaluations framework (brief, in `241`)

`[241:L105-109]`:
> "language models are **inherently non-deterministic, which makes their behaviors hard to predict**.
> The **Evaluations framework** is a **new Swift framework that measures the quality of your
> intelligence features**. With the Evaluations framework, you can **quantify accuracy as you tweak
> your prompts**. Evaluations is built to help app developers like you, **understand the statistical
> impact of changes**, and deliver your app with confidence."

→ deep dives are `wwdc2026-298.txt`, `wwdc2026-299.txt`, `wwdc2026-335.txt` (other agents' scope).

## 1.10 `fm` CLI (as covered in 241)

`[241:L111-121]`:
> "In **macOS 27**, the models are coming to the command line. **The `fm` CLI is a brand new way to use
> Apple Foundation Models for everyday productivity.** You can access **the on-device model and PCC**
> from the terminal, just by using the `fm` command. **`fm` has a nice helper and it lists all the
> features it supports.** I've been using **`fm chat`** to experiment with models, for my app features."

Demo 1: `[241:L117]` — "what does **valley fold** mean in the context origami?"
Demo 2 (scripting) `[241:L119-121]`:
> "I can even **plug `fm` into shell scripts to summarize documents, extract information, or generate
> content.** For example, I have some pictures with random names like this one, `IMG_1234`. Let me just
> ask `fm` to **generate a file name based on the content inside the image**."

→ confirms `fm` accepts **image input** (matches `--image` in `334`).

## 1.11 Python SDK (as covered in 241)

`[241:L122-126]`:
> "if you're a **data scientist or researcher working in the Python ecosystem**, the **FoundationModels
> SDK for Python** has you covered, too. The Python SDK gives you **direct access to the very same
> on-device model that powers the Swift Foundation Models framework**. You can **check model
> availability, or generate a response with just a few lines of Python**. **The SDK has the core
> feature of the Swift framework so you can go from a prompt to a structured response in seconds.**"

Deep dive: **"Build AI-powered scripts with the `fm` CLI and Python SDK"** `[241:L126]` →
`transcripts/wwdc2026-334.txt`.

## 1.12 Closing pointers `[241:L136-140]`

> "check out other videos, for deep dives on all the topics we've introduced here, from the
> **Evaluations framework** to **Private Cloud Compute**, the **enhanced Xcode instrument**, and the
> nitty gritty on **dynamic profiles**."

> "Some great next steps would be to **explore our sample app to learn more about dynamic profiles**,
> and to **start getting familiar with the Evaluations framework**."

Note "**the enhanced Xcode instrument**" → the Foundation Models Instruments template got upgrades in
2026 (see `wwdc2026-243.txt`). The `205` code-along documents the **2025** version of that
instrument in detail (Part 3, Ch. 6) — useful "before" baseline.

---

# PART 2 — `wwdc2026-334.txt` "Foundation Models on macOS" (`fm` CLI + Python SDK)

Presenter: **Eric Gourlaouen**, engineer on the Foundation Models Framework team `[334:L1]`.

## 2.1 Recap framing `[334:L3-11]`

> "At WWDC25, we introduced the Foundation Models Framework in Swift… It was introduced along with
> features like **guided generation, to generate structured outputs**, and **Tool Calling, to let the
> model interact with the context of your app**."

> "With **macOS 27 and iOS 27** come a number of new features to the framework. Like **support for
> passing images in your prompt**. And **access to server models, so that your app can leverage any
> large language model with the same Swift API**." `[334:L6-8]`

> "…it's easy to set up, **with no API key needed and no cloud API costs**. **But until now, those
> models were only available from Swift code.**" `[334:L11-12]`

## 2.2 The `fm` command-line tool

**Ships pre-installed** `[334:L15]`, `[334:L35]`:
> "The `fm` command line tool **comes pre-installed with macOS 27**. It's a fantastic tool to **quickly
> test prompts, right from a terminal, or to incorporate it in automation**. It makes it really easy
> to **test the model with some prompts without rebuilding your project in Xcode**."

> "Starting from **macOS 27**, this command line tool **comes pre-installed on your Mac**. It's
> available right from your **Terminal app**."

### Discovering commands

```bash
fm            # bare invocation prints the list of available commands  [334:L37-38]
```

### Subcommands named in the transcript `[334:L39]`, `[334:L53]`

| Command | Purpose (verbatim-ish) |
|---|---|
| `fm respond` | "prompt the model and return a response" `[334:L39]` |
| `fm chat` | "start an interactive interface" `[334:L39]` |
| `fm schema` | "create a schema" `[334:L39]` |
| `fm schema object` | "Using the command `fm schema object`, I can create a schema" `[334:L53]` |
| *(more)* | "and more" — full list not enumerated on screen |

### `fm chat` slash-commands `[334:L43-45]`

> "`fm chat` comes with a number of commands. For example, with **`/model`**, I can **switch the
> conversation to use the Private Cloud Compute model**. Or, with **`/save`**, I can **save the current
> conversation to resume later**."

| Slash command | Effect |
|---|---|
| `/model` | switch the live conversation to a different model (e.g. PCC) |
| `/save` | save the current conversation to resume later |

> "Interactive sessions with `fm chat` are great for **getting a first pulse of the model**. So if
> you're exploring a new idea, you can pry the model and see how it performs with your prompts."
> `[334:L46-47]`

### `fm respond` options `[334:L48-55]`

> "When you'd rather have **inline responses, like in scripts**, use the command `fm respond` instead.
> Run `fm respond` with a prompt in a terminal, and you'll receive the response from the model as
> output."

| Option (as spoken) | Likely flag (RECONSTRUCTED) | Purpose |
|---|---|---|
| "the **model** option" | `--model` | "lets you prompt the Private Cloud Compute model" `[334:L50]` |
| "the **image** option" | `--image` | "to include an image in your prompt" `[334:L51]` |
| "the **schema** option" | `--schema` | use a schema created by `fm schema object` for structured output `[334:L53]`, `[334:L82]` |
| "the **help** option" | `--help` / `-h` | "To check out all the options, use the help option" `[334:L55]` |
| *(instructions)* | `--instructions` (UNVERIFIED) | "passing my **instructions** and my prompt" `[334:L79]` |

⚠️ **UNVERIFIED:** exact flag spellings (`--model` vs `-m`, long/short forms) are never shown as text.
Only the *semantic names* ("the model option", "the image option", "the schema option", "the help
option") are spoken. Mark all of these as reconstructed in any guide, and tell readers to run
`fm respond --help` on macOS 27.

### Model selection default `[334:L56-59]`

> "the `fm` command line tool lets you use **either the on-device model, or the Apple Foundation Model
> on Private Cloud Compute**. **By default, it uses the on-device model that comes with macOS, and
> that's always available.** You can also use the Apple Foundation Model on Private Cloud Compute,
> **which has usage limits**. It's a much bigger model than the on-device model, so it will **perform
> better on complex problems**."

### Case study: automation script `[334:L60-85]`

Problem: an asset folder full of drafts; keep only final versions; back them up; move old ones to an
archive disk. Motivation quote:

> "Using `fm` here lets me call into a language model that can **sort draft versus final files in my
> script. So that the script works even if the names are messy and are difficult to sort
> predictably.**" `[334:L66-67]`

Script structure as narrated `[334:L77-84]`:
1. Load a list of the files in the working directory.
2. Define a schema **further up** in the script with `fm schema object` — "The structured output will
   have **two fields, a list of final files, and a list of draft files**." `[334:L80-81]`
3. Prompt the model with `fm respond`, "passing my **instructions** and my **prompt**" `[334:L79]`,
   and `fm respond`'s **schema option** to use the schema `[334:L82]`.
4. "**The output of `fm respond` contains a result in a JSON that's generated by the model.**"
   `[334:L83]`
5. Use the JSON result to **copy the final files to backup** and **move the draft files to archive**.

**RECONSTRUCTED** shell sketch (shape only — flags unverified):

```bash
#!/bin/zsh
# RECONSTRUCTED from [334:L77-84]. Flag spellings are NOT shown in the transcript.

WORKDIR="$HOME/Assets"
FILES=$(ls "$WORKDIR")

SCHEMA=$(fm schema object \
  finalFiles:"[string]" \
  draftFiles:"[string]")     # exact `fm schema object` argument syntax UNVERIFIED

RESULT=$(fm respond \
  --instructions "Sort the given file names into final versions and draft versions." \
  --schema "$SCHEMA" \
  "$FILES")                  # RESULT is JSON

# then: jq the two arrays out, cp finals -> backup, mv drafts -> archive
```

⚠️ **Big gap:** `fm schema object`'s actual argument grammar is never shown. Flag as a top open
question — a guide on `fm` needs a live macOS 27 run to fill it in.

Closing nudge `[334:L85]`:
> "There's more to discover with `fm`, so **check out the tool on macOS 27 today, and try using the
> tool in automation**."

## 2.3 The Foundation Models SDK for Python

### Requirements (verbatim, `[334:L88-90]`)

> "You can install it on a Python environment on your Mac, provided that:
> - the **Python version is at least Python 3.10**,
> - that you have **Xcode installed**, and
> - that you're using an **Apple Silicon Mac**.
>
> It's installed through **pip**, or any other package manager of your choice."

✅ **CROSS-CHECK vs. the actual repo** `repos/apple__python-apple-fm-sdk/README.md`:

```
## Requirements                                    (README.md:25-30)

- macOS 26.0+
- Download Xcode 26.0+ and agree to the Xcode and Apple SDKs agreement in the Xcode app.
- Python 3.10+
- Apple Intelligence turned on for a compatible Mac
```

| Claim | Transcript `334` | Repo README | Verdict |
|---|---|---|---|
| Python version | "at least Python 3.10" | `Python 3.10+` | ✅ **agree** |
| Xcode | "you have Xcode installed" | `Xcode 26.0+` **and you must agree to the Xcode and Apple SDKs agreement in the Xcode app** | ⚠️ **README is stricter** — the license-agreement step is a real footgun the talk omits |
| Hardware | "Apple Silicon Mac" | "Apple Intelligence turned on for a compatible Mac" | ✅ compatible (README adds the AI-enabled requirement) |
| OS | *(session is about macOS 27)* | **macOS 26.0+** | ⚠️ **DISCREPANCY worth noting:** the **Python SDK works on macOS 26**, unlike the `fm` CLI which is macOS-27-preinstalled. The talk implies both are "new on macOS 27". |

Install (repo, README.md:38-40):
```bash
pip install apple-fm-sdk
```
Package **import name** (README.md:52): `import apple_fm_sdk as fm` — note the alias `fm`, which
explains why the presenter says "`fm.generable`" / "`fm.respond`".

Dev install (README.md:107-132):
```bash
git clone https://github.com/apple/python-apple-fm-sdk
cd python-apple-fm-sdk
uv venv
source .venv/bin/activate
uv sync
uv pip install -e .
pytest
```

### Feature parity claims `[334:L91-95]`

> "**The Python SDK includes the core features of the framework.** If you've already used it in Swift,
> **the APIs and abstractions will quickly feel familiar.** You can use it to prompt a model with
> **text inputs and image inputs**, and you can use it to **stream responses**. Just like in Swift, you
> can use **guided generation** to have the model generate structured outputs. And you can use **tool
> calling** to enable the model to interact with code."

✅ README (lines 10-18) lists, verbatim:
```
- Evaluate Swift Foundation Models app features by running batch inference and analyzing results from Python
- Perform on-device inference with the system foundation model
- Stream real-time text generation responses
- Use guided generation with structured output schemas and constraints
- Get type-safe responses using Python decorators for guided generation
- Configure custom model settings for different model options
- Process transcripts exported from Swift apps for quality analysis
```
⚠️ **Note:** the README does **not** list tool calling, while the transcript does `[334:L95]`. Possible
version skew (README may predate). Flag as an open question. Also note **"Process transcripts
exported from Swift apps"** — a Swift→Python transcript interop path that the talk never mentions.
The repo has `examples/transcript_processing.py`.

### Basic prompting `[334:L100-104]`

> "Prompting the model is done just like in Swift. I start by creating a **`LanguageModelSession`**, to
> which I can **pass instructions if I'd like**. Then, I call **`session.respond`, passing my prompt as
> an argument**. The result of method contains the output of the model."

✅ **VERBATIM from README.md:55-72:**

```python
import apple_fm_sdk as fm
import asyncio

async def main():
    # Get the default system foundation model
    model = fm.SystemLanguageModel()

    # Check if the model is available
    is_available, reason = model.is_available()
    if is_available:
        # Create a session
        session = fm.LanguageModelSession()

        # Generate a response
        response = await session.respond("Hello, how are you?")
        print(f"Model response: {response}")
    else:
        print(f"Foundation Models not available: {reason}")

# Run async function
asyncio.run(main())
```

**Concrete API facts from that block:**
- `fm.SystemLanguageModel()` — a *constructor call*, not a `.default` static (contrast with Swift's
  `SystemLanguageModel.default`).
- **`model.is_available()` returns a 2-tuple `(is_available: bool, reason)`** — a much flatter design
  than Swift's `availability` enum with associated `UnavailableReason`.
- `fm.LanguageModelSession()` ; `await session.respond(prompt)` — async, awaited.

### Guided generation in Python `[334:L107-111]`

> "Just like in the Swift Framework and in the command line tool, I can also **constrain the model to
> produce structured outputs**. For example, in this code, I'm using guided generation to ensure the
> output of the model is captured in an **`ItemsSuggestion`** object. Here, using the
> **`fm.generable` decorator**, I define the desired output structure, and I pass it to
> **`fm.respond` as the `generating` argument**."

✅ **VERBATIM from README.md:78-101:**

```python
import apple_fm_sdk as fm

@fm.generable # This decorator signals this type be generated by a model
class Cat:
    name: str
    age:int = fm.guide("Age in years", range=(0, 20))

async def generate_cat():
    # Get the default system foundation model
    model = fm.SystemLanguageModel()

    # Check if the model is available
    is_available, reason = model.is_available()
    if is_available:
        # Create a session
        session = fm.LanguageModelSession()

        # Generate a response of the type Cat
        cat = await session.respond("Generate an adorable rescue cat", generating=Cat)
        print(f"Model response: {cat}")
    else:
        print(f"Foundation Models not available: {reason}")
```

⚠️ **DISCREPANCY (transcript vs. repo):** the presenter says "I pass it to **`fm.respond`** as the
generating argument" `[334:L110-111]`, but the README shows **`session.respond(..., generating=Cat)`**.
The README is the ground truth — `respond` is a **session method**, not a module function. Treat the
presenter's phrasing as shorthand.

**Python ↔ Swift mapping table** (derived, high confidence):

| Swift | Python |
|---|---|
| `@Generable struct Cat { … }` | `@fm.generable` on a `class Cat` with annotated attributes |
| `@Guide(description: "Age in years", 0...20) var age: Int` | `age: int = fm.guide("Age in years", range=(0, 20))` |
| `SystemLanguageModel.default` | `fm.SystemLanguageModel()` |
| `model.availability` → enum | `model.is_available()` → `(bool, reason)` |
| `LanguageModelSession(instructions:)` | `fm.LanguageModelSession()` (+ instructions arg) |
| `try await session.respond(to:generating:)` | `await session.respond(prompt, generating=Cat)` |

Note `fm.guide` takes the **description positionally** and constraints as **kwargs** (`range=(0,20)`),
whereas Swift's `@Guide` takes `description:` labelled plus a `RangeExpression`.

### Python eval-pipeline case study `[334:L112-157]`

Scenario: grocery-ordering app; "predict what users would like to add to their cart based on their
previous orders" `[334:L115]`, with two correctness requirements `[334:L116-117]`:
1. "the output **reliably works off of the previous orders**"
2. "the prediction **accounts for any items already in the cart**"

Pipeline as described `[334:L124-132]`:
1. "First, I used **a large server model to generate evaluation data**. I now have some **inputs**, and
   for each of those, **data on what I expect in the output**."
2. "I'll write **a number of implementations that use different prompts**."
3. "for each of my evaluation inputs, I'll **generate outputs using each of those different
   implementations**."
4. "I'll then save this data as **rows in a Pandas DataFrame**."
5. "I've designed some **judge functions that rely on a server model**. They will **score each output
   on the criteria of my choice**."
6. "I'll then save those **metrics in the Pandas DataFrame**."
7. "I can now **generate some charts** to see them visually." (matplotlib `[334:L144]`)

Three prompt variants under test `[334:L135-139]`:
- #1 "a **very minimal** prompt"
- #2 "a **more descriptive** prompt, and describes the task more in detail"
- #3 "the **most comprehensive** prompts, and describes **a list of rules** to the model"

### 🔑 The findings — a genuinely valuable, counter-intuitive result `[334:L148-152]`

> "First, by looking at the **errors generated by setup**, I can see that **the detailed prompt leads to
> a high percentage of generation errors**. **This can happen, for example, when we reach the model's
> max context window size.**"

> "Next, we can see that **the two less detailed prompts tend to lead to excess items added to the
> cart**, while **the more detailed one has less excess items**. However, **with the more detailed
> prompts, we tend to miss more items that were expected**."

> "The **first prompt also tends to lead to more hallucinated items** added to the cart."

**Lesson to teach:** longer/more-rule-heavy prompts trade *precision for recall* AND raise
**context-window-exceeded generation errors**. There is no monotone "more prompt = better". This is
the best empirical claim in either 2026 transcript.

Ecosystem/velocity argument `[334:L153-157]`:
> "With Python, I can make those iterations quickly **right from my notebook without having to rebuild
> the whole project**."

### Swift vs Python for evaluation `[334:L120-123]`

> "To evaluate their prompt and iterate, Swift developers can leverage the **Evaluations framework**.
> It's **available with Xcode 27**, and it makes it easy to create evaluations, and **track the
> accuracy of your features across multiple iterations**. But many **data scientists might be more
> familiar with Python than with Swift**. If you fall under this scenario, let me show you how I can
> perform this analysis in Python by **using the Python SDK from a Jupyter Notebook**."

→ **Version gate: Evaluations framework requires Xcode 27.**

### Recommended next steps `[334:L163-169]`
1. "start by **exploring the command line tool from the Terminal app**."
2. "to learn more about how to use the Python SDK, **head to the GitHub repository**. You'll find some
   **example snippets and some documentation**." → repo has `examples/simple_inference.py`,
   `examples/streaming_example.py`, `examples/transcript_processing.py`, and a `docs/` Sphinx build
   (`docs/Makefile`, `docs/source`, `docs/requirements.txt`). Docs site per README.md:46 =
   `https://apple.github.io/python-apple-fm-sdk/`.
3. "**create an evaluation pipeline**… quantify the results of the model against an evaluation dataset."

Repo status note (README.md:32-34): **"This project is not yet taking contributions. Stay tuned!"**

---

# PART 3 — `meet-with-apple-205.txt` — FM Framework Code-Along (FULL transcription of the code)

Presenter: **Shashank**, Technology Evangelist at Apple `[205:L2-3]`. Format: live code-along with a
web guide, Slido Q&A, and an expert team behind the scenes `[205:L5-6]`, `[205:L51]`.

⚠️ **This is the iOS 26 / Xcode 26 baseline.** Every API here is the 2025 surface. It is *still valid*
in 2026 (nothing here is described as removed), but the 2026 additions from Parts 1-2 sit on top.

## 3.0 Setup, requirements, project layout

### Value proposition (verbatim, `[205:L12-16]`)

> "For developers, this on-device approach has major advantages. Because everything runs locally,
> **user data remains private**. Your features work **entirely offline** with **no accounts to set up or
> API keys to manage**. There's **no cost to you or someone using the app** for any of these requests.
> And since it's all part of the OS, there's **no impact on your app size**."

### System requirements (verbatim, `[205:L55-57]`)

> "you'll need an **Apple Silicon based Mac running macOS Tahoe and Xcode 26**. You'll also need to make
> sure that **Apple intelligence is turned on under settings**. I'll be building and running the app
> directly on my Mac today, but you can also use **Xcode 26 with a recent iPhone running iOS 26** as
> your target."

### The three resources `[205:L41-51]`
1. **Xcode starter project** — "has all the boilerplate UI and assets ready to go"; under Resources on
   the developer.apple.com page / linked from the YouTube description.
2. **A step-by-step web guide** — "**This is your source of truth** with all the instructions and code
   snippets. You can simply copy paste these to avoid typos."
3. Live presenter + expert team.

### Project structure (from the tour, `[205:L77-113]`)

```
FoundationModelsCodeAlong/
├── Playgrounds/
│   └── Playground.swift          ← "iterate on prompts and test FM APIs in isolation
│                                     without having to build and run our entire app"  [205:L78-81]
├── Models/
│   ├── Itinerary.swift           ← the @Generable Itinerary / DayPlan / Activity types
│   └── ModelData.swift           ← ModelData.landmarks (Serengeti, Grand Canyon, Sahara Desert, …)
├── ViewModels/
│   ├── ItineraryGenerator.swift  ← "All the core logic for creating and managing foundation model
│   │                                sessions, calling the framework APIs and processing the results
│   │                                will live right here."  [205:L84]
│   └── FindPointsOfInterestTool.swift
└── Views/
    ├── LandmarksView.swift       ← "We won't be touching this file today."  [205:L103]
    ├── 1_LandmarkDetailView.swift  ← "check if the Foundation Models Framework is available on
    │                                  device and decide what UI to show based on that"  [205:L108]
    ├── 2_LandmarkTripView.swift  ← "present the generate itinerary button" + first raw-text display
    └── 3_ItineraryView.swift     ← renders the rich structured itinerary
```
*(File numbering: "the key files we'll be editing are numbered" `[205:L88]`; the presenter refers to
"file number three" for `ItineraryView` `[205:L483]` and "the second number[ed] file in the views
folder" for `LandmarkTripView` `[205:L470]`.)*

### The marker-comment workflow (a genuinely reusable teaching pattern) `[205:L90-95]`

> "you'll notice there are **special comments formatted this way. `MARK: Code-Along Chapter <N>`**. Each
> number here corresponds directly to the chapter and section with the same number in your Code Along
> guide. You can use the **Xcode Find Navigator to search for the chapter number to see all the
> outstanding code changes**… **As we complete each step, we'll keep deleting these comments so we can
> track progress** throughout the Code Along."

### The 3-step methodology (verbatim, `[205:L96-98]`)

> "we'll follow three simple steps. **First, experiment in the playground. Second, implement the core
> logic in the view model, and finally, display the results in the view.**"

### Six chapters `[205:L115-123]`
1. Basics — prompting the model for text
2. Structured output (`@Generable`)
3. Prompting techniques (PromptBuilder, one-shot)
4. Streaming
5. Tool calling
6. Performance optimization

---

## 3.1 CHAPTER 1 — Sessions, prompts, instructions, availability

### 1.1 First prompt in a Playground

Three steps `[205:L146-157]`: (1) import, (2) create a playground, (3) create a session, then prompt.

**`#Playground` macro mechanics** `[205:L148-152]`:
> "As soon as you use a **playground macro** to create a playground, you'll see a **canvas show up on
> the right**. If it doesn't, you can always click on **editor options and ensure that there's a check
> mark next to canvas**. you can click the **refresh button** and what that does is **run all the code
> contained within the playground block**."

**VERBATIM-ISH** — `Playgrounds/Playground.swift`, chapter 1.1:

```swift
import FoundationModels
import Playgrounds

#Playground {
    let session = LanguageModelSession()

    let response = try await session.respond(
        to: "Generate a 3-day itinerary to Paris."
    )
}
```

Canvas observations `[205:L154-163]`:
- Inspecting `session` in the canvas shows two properties: **`tools`** ("which we'll discuss in a later
  chapter") and **`transcript`** ("which includes all the conversations that you have with the model").
- `response` has properties **`prompt`** and **`content`**. `content` is **`String`** at this stage.
- Actual model output began: *"Certainly here's a 3-day itinerary for exploring Paris, highlighting
  some of the city's most iconic sites and experience"* with "day by day plans for day one, morning,
  afternoon, and so on" `[205:L163]`.

**FIRST-CALL LATENCY (important, `[205:L166-170]`):**
> "When you make the very first call to `session.respond`, **you might notice that there's a slight
> delay. This is because the on-device language model needs to be loaded into memory before it can
> process your request. Our first request triggers a system to load the model, which causes the
> initial latency.** We'll see how to address this in a later chapter." → chapter 6, `prewarm()`.

Privacy restatement `[205:L173-174]`:
> "**the entire itinerary without any data ever leaving your device. It's completely private and works
> offline.**"

**Model feedback affordance** `[205:L176-177]`:
> "We are always interested in improving the model, and **if you want to provide feedback, you can
> always use these buttons right here in Canvas to share your feedback with us.**"

✅ **Cross-check (forums, thread 791250, Apple-authored, 01 Jul 2025):** confirms and details this —
*"Starting in macOS/iOS 26 Beta 4, the best way to provide feedback is to use `#Playground` in Xcode…
In the canvas on the right, click the **thumbs-up icon** to the right of the response."* So the
canvas buttons are **thumbs-up / thumbs-down feedback**, gated on **beta 4+**.

### 1.2 Instructions

**VERBATIM-ISH** `[205:L186-189]`:

```swift
#Playground {
    let instructions = """
        Your job is to create an itinerary for the user.
        Each day needs an activity, hotel, and restaurant.
        Always include a title, a short description, and a day-by-day plan.
        """

    let session = LanguageModelSession(instructions: instructions)

    let response = try await session.respond(
        to: "Generate a 3-day itinerary to Paris."
    )
}
```
*(The instructions string is read out almost word for word at `[205:L186-188]` and re-read at
`[205:L280-282]`; line breaks are my formatting. The parameter label is stated: "We can pass these
instructions into the language model session using the **instruction argument**" `[205:L189]` — the
real label is `instructions:`.)*

Canvas auto-refresh note `[205:L190]`: "**the canvas will automatically detect code changes and update
our results**."

### 🔑 Instructions vs. Prompts (verbatim, `[205:L193-199]`) — the most quotable passage

> "**Instructions can be used to define a persona, set rules, and specify desired format for the
> response. This should come from the developer. Prompts, on the other hand, can come from someone
> using the app. The model is trained to obey instructions over prompts, and this can help protect
> against prompt injection attacks where the user may ask the model to ignore guidance provided in the
> prompt. As a rule, keep the instructions static and avoid inserting user input into them.**"

> "**Also note that instructions are maintained throughout the session's life. Every interaction is
> recorded in the session's transcript, and the initial instructions are always the first entry.**"

Distilled rules for a guide:
| | Instructions | Prompt |
|---|---|---|
| Author | **developer** | **end user** (potentially) |
| Purpose | persona, rules, desired format | the actual request |
| Priority | **model trained to obey instructions over prompts** | lower |
| Mutability | **keep static** | dynamic |
| User input | **never interpolate** (prompt-injection defense) | fine |
| Transcript position | **always the first entry** | after |

### 1.3 Availability

**VERBATIM-ISH** — the availability switch `[205:L208-228]`. The presenter adds a *second*
`#Playground` block in the same file ("a neat feature of playground is **you can add multiple of these
in the same Swift file**" `[205:L211]`; "**The second playground will show up as a second tab** here on
our canvas" `[205:L216]`).

```swift
#Playground {
    let model = SystemLanguageModel.default

    switch model.availability {
    case .available:
        // "you have a green light… the model is loaded and you're ready to make
        //  generation requests."
        print("Foundation model is available and ready to go.")

    case .unavailable(.deviceNotEligible):
        // "the model doesn't support Apple Intelligence. You should gracefully hide the
        //  generative UI and show an alternate experience."
        break

    case .unavailable(.appleIntelligenceNotEnabled):
        // "the device is capable, but Apple Intelligence is turned off in settings.
        //  This is your chance to prompt the user to enable it."
        break

    case .unavailable(.modelNotReady):
        // "this is a temporary state, likely because the model assets are still
        //  downloading. The best practice is to tell the user to try again."
        break

    @unknown default:
        break
    }
}
```

**Enum cases, exactly as narrated `[205:L220-228]`:**

| Case | Meaning (verbatim) | Recommended handling (verbatim) |
|---|---|---|
| `.available` | "you have a green light… the model is loaded and you're ready to make generation requests" | proceed |
| `.unavailable(.deviceNotEligible)` | "the model doesn't support Apple Intelligence" *(sic — device doesn't support)* | "**gracefully hide the generative UI and show an alternate experience**" |
| `.unavailable(.appleIntelligenceNotEnabled)` | "the device is capable, but **Apple Intelligence is turned off in settings**" | "**This is your chance to prompt the user to enable it.**" |
| `.unavailable(.modelNotReady)` | "**a temporary state, likely because the model assets are still downloading**" | "**tell the user to try again**" |

The three failure motivations were also stated up front `[205:L202-203]`:
> "the device may not even support Apple intelligence… the device may support Apple intelligence, but
> **the user has not enabled it**… or **the model assets are still downloading and they're not ready
> for use yet**."

⚠️ **`@unknown default` is my addition** (Swift requirement for non-frozen enums). Not stated.

### 1.4 App wiring — `LandmarkDetailView.swift`

**VERBATIM-ISH** `[205:L239-249]`:

```swift
// Views/LandmarkDetailView.swift
private let model = SystemLanguageModel.default

// …then, in the view body, replace the placeholder availability value with:
switch model.availability { … }
```
> "we say **`private let model = SystemLanguageModel.default`**. This is **exactly the same line of code
> we used in our playground**." `[205:L240-242]`

### 🔑 Testing availability without extra devices — Xcode scheme setting `[205:L251-257]`

> "we've added these availability checks… **but how do you test them? You may not have access to
> multiple test devices. Thankfully, there's an easy way. Right here in the scheme settings in the
> project, there's an option to **simulate unavailability**… Click on `FoundationModelsCodeAlong` →
> **Edit Scheme** → scroll down → **"Simulated Foundation Models availability"**. If you click this,
> there are a few different options, and **these options should be familiar to you because these are
> the cases we covered in the playground**."

**Exact UI path:** *Scheme menu → Edit Scheme… → (Run action, scroll down) → **Simulated Foundation
Models availability*** with a picker whose options mirror the `UnavailableReason` cases. The presenter
selects **"Apple Intelligence Not Enabled"** and gets the app message:
> "**Trip Planner is unavailable because Apple Intelligence has not been turned on.**" `[205:L258]`

This is a **high-value, low-discoverability Xcode feature** — deserves a guide callout.

### 1.5 App wiring — `ItineraryGenerator.swift` (chapter 1 state)

**RECONSTRUCTED** from `[205:L273-295]`:

```swift
// ViewModels/ItineraryGenerator.swift — end of Chapter 1
// RECONSTRUCTED. @Observable/@MainActor are inferred (SwiftUI view model), not stated.
import FoundationModels
import Observation

@Observable
@MainActor
final class ItineraryGenerator {
    private let landmark: Landmark
    private var session: LanguageModelSession

    var itineraryContent: String?          // chapter 1 only; becomes `itinerary` in ch.2

    init(landmark: Landmark) {
        self.landmark = landmark
        let instructions = """
            Your job is to create an itinerary for the user.
            Each day needs an activity, hotel, and restaurant.
            Always include a title, a short description, and a day-by-day plan.
            """
        self.session = LanguageModelSession(instructions: instructions)
    }

    func generateItinerary(dayCount: Int = 3) async throws {
        let prompt = "Generate a \(dayCount)-day itinerary to \(landmark.name)."
        let response = try await session.respond(to: prompt)
        itineraryContent = response.content
    }
}
```

Narration backing:
- "we define a variable called **`session`** for `LanguageModelSession`" `[205:L275]`
- "**Xcode will remind us that we have not initialized a session. So we are going to initialize this
  session right here in the init**" `[205:L276-277]`
- "**`let prompt = "Generate a \(dayCount)-day itinerary to \(landmark.name)."`**. **Day count here
  defaults to three** and then `landmark.name` is the name of the landmark that the user clicks on"
  `[205:L287-290]`
- "**`let response = try await session.respond(to: prompt)`**" `[205:L292-293]`
- "the response variable has a property `.content`… which had all the natural unstructured text, which
  is a **String**, and we assign it to `itineraryContent`" `[205:L294-295]`

### 1.6 App wiring — `LandmarkTripView.swift` (chapter 1 state)

**RECONSTRUCTED** from `[205:L306-334]`:

```swift
// Views/LandmarkTripView.swift — end of Chapter 1  (RECONSTRUCTED)
struct LandmarkTripView: View {
    let landmark: Landmark
    @State private var itineraryGenerator: ItineraryGenerator?
    @State private var requestedItinerary = false

    var body: some View {
        VStack {
            if !requestedItinerary {
                Text(landmark.name)
                Text(landmark.shortDescription)
            } else if let content = itineraryGenerator?.itineraryContent {
                Text(content)
            }

            Button("Generate Itinerary") {
                requestedItinerary = true
                Task {
                    try? await itineraryGenerator?.generateItinerary()
                }
            }
        }
        .task {
            let generator = ItineraryGenerator(landmark: landmark)
            self.itineraryGenerator = generator
        }
    }
}
```

Narration backing:
- "add a **local variable for the itinerary generator class**" `[205:L306-307]`
- "**create an instance of this when the view is loaded**… under **`.task` modifier**… `let generator =
  ItineraryGenerator(landmark)`, which is the ViewModel class, and we **pass in the landmark**"
  `[205:L308-310]`
- "By default, we have a **Boolean variable here called `requestedItinerary`. It is set to false**."
  `[205:L315-316]`
- "**`if let content = itineraryGenerator.itineraryContent`**" `[205:L323`]
- Button: "**currently this button is hidden. So we'll need to make two minor code changes: one, we want
  to show the button**… and then we need to insert code here to generate the itinerary when the user
  taps on the button… **`await itineraryGenerator.generateItinerary()`**" `[205:L329-334]`

⚠️ **Transcript error to NOT copy:** at `[205:L322]` the presenter says "**when the requested itinerary
is set to false, we need to load up a new view**" — clearly a mis-speak for `true`. My reconstruction
above uses the correct logic.

### Chapter 1 recap `[205:L348-350]`
> "we learned how to **create a session and prompt the model** for a basic text response. We saw how to
> **provide instructions to guide the model's output** and we covered how to **handle different
> availability states using the availability API**."

And the pain point that motivates chapter 2 `[205:L343-344]`:
> "**what we have here is a wall of text. What if I wanted to pull out a hotel name and show it on a
> map? This isn't the rich experience that we want.**"

---

## 3.2 CHAPTER 2 — Guided generation (`@Generable` / `@Guide`)

### Framing (verbatim, `[205:L353-363]`)

> "By default, they give us **unstructured text**… how would you reliably extract the hotel for day one
> to plot it on a map? **You'd have to write complex string parsing code that could break if the
> model's output changed.**"

> "This is where **guided generation** comes in. The Foundation Models Framework provides APIs that
> allow you to **specify exactly what your output should look like**. If you have a Swift struct, you
> can simply apply **`@Generable`** to it. And this lets the model **generate structured data using
> native Swift types**."

### 2.1 `SimpleItinerary`

**VERBATIM-ISH** `[205:L374-387]`:

```swift
@Generable
struct SimpleItinerary {
    @Guide(description: "An exciting name for the trip.")
    var title: String

    @Guide(description: "A short and engaging description for the trip.")
    var description: String

    @Guide(description: "A day-by-day plan.")     // description reconstructed
    var days: [String]
}

#Playground {
    let session = LanguageModelSession(instructions: instructions)

    let response = try await session.respond(
        to: "Generate a 3-day itinerary to Paris.",
        generating: SimpleItinerary.self
    )
}
```

Narration `[205:L376-387]`:
- "this struct has a few different properties. It has a **`title`, which is of type `String`**. It has a
  **`description`, which is of type `String`**. And it has **`days`, which is an array of `String`**."
- "We want the model to generate these fields and we can provide it additional information by
  **providing guides**. The guide has a **`description` argument** which says, '**an exciting name for
  the trip**.' This tells the model that it has to generate a title for this variable and similarly we
  have description, '**a short and engaging description for the trip**'…"
- "we can do that using the **`generating` argument**. So previously we had `session.respond` and just
  the prompt. So I'm going to add a new argument called **`generating`** and provide
  **`SimpleItinerary.self`**."

⚠️ At `[205:L382]` the presenter says "and similarly for **day count**", which is almost certainly a
mis-speak for the `days` guide. I've marked the third `@Guide` description as reconstructed.

Canvas result `[205:L392-401]`:
> "Previously, this `content` was a string. If you look carefully here, it says **this is a struct
> `SimpleItinerary`**… **the output one to one matches with the struct that we just defined**… title,
> which is '**Parisian Bliss**'… `days`, which is an array of `String` with day-by-day activity plan."

**Key fact: `response.content` becomes the `@Generable` type itself** when `generating:` is supplied.

### 2.2 The full nested `Itinerary` type — `Models/Itinerary.swift`

**RECONSTRUCTED** from the walkthrough at `[205:L413-427]` (the presenter reads the shape aloud but not
the literal source):

```swift
// Models/Itinerary.swift — RECONSTRUCTED from [205:L413-427]
@Generable
struct Itinerary {
    @Guide(description: "An exciting name for the trip.")
    var title: String

    @Guide(.anyOf(ModelData.landmarkNames))     // exact expression UNVERIFIED — see below
    var destinationName: String

    @Guide(description: "A short and engaging description for the trip.")
    var description: String

    @Guide(description: "The rationale for why this itinerary suits the traveler.")
    var rationale: String

    @Guide(description: "A day-by-day plan.")
    var days: [DayPlan]
}

@Generable
struct DayPlan {
    var title: String
    var subtitle: String
    var destination: String
    var activities: [Activity]
}

@Generable
struct Activity {
    var type: ActivityKind
    var title: String
    var description: String
}

@Generable
enum ActivityKind {
    case sightseeing
    case foodAndDining
    case shopping
    case hotelAndLodging
}
```

Narration, line by line:
- "**It also has a `title` which is of type `String`. It has a `description`, it has `rationale`.** And
  if you take a closer look at `days`, you'll see that **it's no longer an array of `String`. It is
  actually an array of `DayPlan`, which in turn is its own struct.**" `[205:L417-419]`
- "**It has its own `title`, its own `subtitle`, its own `destination` and an `activities`, which is an
  array of another struct called `Activity`, which has a `type`, `title`, `description`** — and `type`
  here happens to be **an enum, which is also `@Generable`**." `[205:L420]`
- "**The enum is a great way to have the model generate specific cases that are predefined.** For
  example, here, the type can only be **sightseeing, food and dining, shopping, hotel and lodging**."
  `[205:L421-422]`
- "there is **another way to constrain what the model can generate**. We can use enums or here for
  `destinationName`. We have a guide that says **`anyOf`** and we provide **`ModelData.landmark[s]`**.
  **What this tells the model is that it has to generate a destination name that is one of the
  landmarks that we see when we open up the app.** This includes **the Serengeti, the Grand Canyon,
  Sahara Desert** and so on. **So the output must be one of these.**" `[205:L423-428]`

**Two distinct constraint mechanisms taught here — worth a guide table:**

| Mechanism | When to use | Example |
|---|---|---|
| `@Generable enum` | fixed, compile-time-known set of cases | `ActivityKind` |
| `@Guide(.anyOf(...))` on a `String` | set known only at **runtime**, from app data | `destinationName` constrained to `ModelData.landmark[Names]` |

⚠️ `.anyOf` exact spelling and whether the array is `[String]` of names is **RECONSTRUCTED** — the
presenter says "a guide that says **any of** and we provide **model data dot landmark**".

### 🔑 Composability (verbatim, `[205:L441-442]`)

> "**The key thing to note here is that when you apply `@Generable`, it is completely composable. The
> framework understands how to build this entire complex object from the top down, all while
> guaranteeing structural correctness.**"

### 🔑 Constrained decoding (verbatim, `[205:L489-493]`)

> "the key benefit of guided generation is that it **fundamentally guarantees structural correctness**.
> It uses a technique called **constraint[ed] decoding** to do that. What it does is **give you control
> over what the model should generate, whether that be strings or numbers or arrays or even a custom
> data structure that you define**."

> "This also means that **our prompts can be a lot simpler and more focused on the desired behavior
> instead of prompting the model for specific output formats. This also tends to improve model accuracy
> [and] allow for optimizations that speed up inference.**"

### A live gotcha from the demo `[205:L432-435]`

> "because if you recall, we said the **destination name should be one of the names from the list.
> Paris is not part of the list.** So I'm going to change it to something that is actually on the list.
> How about **Grand Canyon**?"

**Footgun to teach:** when you constrain a field with `@Guide(.anyOf(...))`, a prompt that names a
value outside the set produces a mismatch. Keep prompt vocabulary and guide vocabulary consistent.

### 2.3 App wiring changes `[205:L449-464]`

1. `var itineraryContent: String?` → **`var itinerary: Itinerary?`**
2. `session.respond(to: prompt)` → **`session.respond(to: prompt, generating: Itinerary.self)`**
3. **Delete the structural guidance from the instructions.** Verbatim `[205:L459-463]`:
   > "the final change we'll need to make is to **remove additional structural guidance that we are
   > providing in our instructions**. Notice how we say 'each day needs an activity, hotel and
   > restaurant, always include a title, short description, day by day'. **But all of this information
   > is already in our itinerary `@Generable` struct. We don't need to provide it again in our
   > instructions. So… another benefit of using generables is you can make your prompts much simpler,
   > which can help improve performance as well.**"

   → After chapter 2 the instructions collapse to roughly:
   ```swift
   let instructions = "Your job is to create an itinerary for the user."
   ```

### 2.4 View wiring `[205:L471-487]`

```swift
// Views/LandmarkTripView.swift  (RECONSTRUCTED)
} else if let itinerary = itineraryGenerator.itinerary {
    ItineraryView(landmark: landmark, itinerary: itinerary)
}
```
> "**`ItineraryView`, which takes in a `landmark` and takes in the generated `itinerary`**"
> `[205:L479-481]`

`ItineraryView` structure `[205:L486]`:
> "it can extract the itinerary `title`, its `description`, populate… and when it extracts the
> **day-by-day activity, there is a dedicated view called `DayView`** that can show that and we use
> **`ForEach` to loop through these** and extract all the properties and lay it out. **Notice this is
> so much simpler than being able to parse strings and update it.**"

---

## 3.3 CHAPTER 3 — Prompting techniques (PromptBuilder + one-shot)

### Framing `[205:L504-506]`
> "**While a good prompt tells the model what to do, sometimes it's more effective to just show it. We
> can include a high quality example as an instance of our `@Generable` type directly in a prompt.**"

### 3.1 PromptBuilder — `Prompt { }` result builder

**VERBATIM-ISH** `[205:L521-530]`:

```swift
#Playground {
    let kidFriendly = true

    let prompt = Prompt {
        "Generate a 3-day itinerary to Grand Canyon."
        if kidFriendly {
            "The itinerary must be kid-friendly."
        }
    }

    let response = try await session.respond(
        to: prompt,
        generating: Itinerary.self
    )
}
```

Narration `[205:L521-528]`:
- "Previously… under `session.respond`, we provided the `to` argument with '**generate a three-day
  itinerary to Grand Canyon**' **in the format of a string**. But instead, we can define the prompt
  **not as a string, but using the prompt builder API and passing the values to a closure.**"
- "**The key benefit is that it can now include things like Swift conditionals.** So right up top here,
  we have a variable… which is a **Boolean, which is currently set to `true`**. And then **within the
  Prompt Builder API, I use this Boolean to conditionally update my prompt. So if the kid-friendly
  Boolean is true, then we inject this additional information into the prompt, which is '**the itinerary
  must be kid-friendly**'."

Verified effect (from the canvas) `[205:L534]` — the generated `rationale` read:
> "*this itinerary provides a safe, engaging and educational experience for children, ensuring they
> enjoy the natural beauty of Grand Canyon while being supported by age appropriate activities and
> accommodation.*"

Why it matters `[205:L536]`:
> "the benefit of this again is that **you can have these prompts be dynamic. This could be something
> that the user selects on the app or it could be something that you learn as a developer from the
> user's preference and update a prompt.**"

### 3.2 One-shot prompting with a `@Generable` INSTANCE

**VERBATIM-ISH** `[205:L542-556]`:

```swift
let prompt = Prompt {
    "Generate a 3-day itinerary to Grand Canyon."
    if kidFriendly {
        "The itinerary must be kid-friendly."
    }
    "Here is an example of the desired format, but don't copy its content."
    Itinerary.exampleTripToJapan
}
```

### 🔑 THE key API fact hidden in this chapter

`Itinerary.exampleTripToJapan` is **an instance of the `@Generable` struct**, dropped directly into the
`Prompt { }` builder — i.e. **`@Generable` types are usable as prompt components** (they conform to
whatever `PromptRepresentable`-style protocol the builder accepts). Verbatim `[205:L548-551]`:

> "you can command click on this or head over to models folder, click on itinerary and scroll down and
> you'll see that **`exampleTripToJapan` is defined right here. The first thing that you'll notice that
> this is not a big string that includes an example. This is actually an instance of the `Itinerary`
> `@Generable` with all its properties populated.** You'll see that we have a `title`, a
> `destinationName`, `description`, `rationale`, `days`, and **all the properties manually populated**."

And crucially `[205:L570-572]`:
> "we also include this additional information whereby [we] introduce `Itinerary.exampleTripToJapan`,
> which is of the type `Itinerary`. **So not only does it include all the guidance, but also the schema
> that's part of this prompt now.**"

→ **This is what makes `includeSchemaInPrompt: false` safe in chapter 6.** Embedding an instance
implicitly carries the schema.

### The "golden example" rationale (verbatim, `[205:L553-557]`)

> "**The most important part is that we are embedding this `Itinerary.exampleTripToJapan` directly into
> the prompt. This is our golden example. We're also telling the model explicitly, don't copy its
> content. We wanted to learn from the style and structure and not just repeat the data.**"

### The `@Generable` vs one-shot division of labour (verbatim, `[205:L584-586]`)

> "**While `@Generable` enforces the structure, the one-shot example teaches the model about
> relationship and the style within the structure. The model also uses the provided example for the
> desired tone of voice, ensuring that the generated text aligns with the tone you want to set for the
> app. While the difference in output may not always be dramatic, it's an important way to
> significantly improve the quality of your generated content.**"

*(Note the honest hedge: "the difference in output may not always be dramatic.")*

---

## 3.4 CHAPTER 4 — Snapshot streaming

> "This section **doesn't include a playground component** because it's easy to appreciate the
> streaming responses directly in the app." `[205:L606]`

### 4.1 `PartiallyGenerated`

**VERBATIM-ISH** `[205:L609-611]`:

```swift
// ViewModels/ItineraryGenerator.swift
var itinerary: Itinerary.PartiallyGenerated?
```

### 🔑 Definition (verbatim, `[205:L611-613]`)

> "**So what is `PartiallyGenerated`? Think of this as a mirror version of our struct where every single
> property is an optional. `@Generable` defines this automatically for us. It's a perfect way to
> represent data that arrives over time.**"

So for every `@Generable T`, the macro synthesizes a nested type **`T.PartiallyGenerated`** with all
properties optional. This applies to **nested types too**: `DayPlan.PartiallyGenerated`,
`Activity.PartiallyGenerated` `[205:L643-644]`.

### 4.2 `streamResponse`

**VERBATIM-ISH** `[205:L620-630]`:

```swift
func generateItinerary(dayCount: Int = 3) async throws {
    let prompt = Prompt { /* … as in chapter 3 … */ }

    let stream = session.streamResponse(
        to: prompt,
        generating: Itinerary.self
    )

    for try await partialResponse in stream {
        itinerary = partialResponse.content
    }
}
```

Narration `[205:L623-630]`:
> "we replaced `session.respond` with **`session.streamResponse`** and **kept the rest of the argument
> same**. So you still pass in a prompt, you still provide the `generating` argument with the
> `Itinerary`. **But we don't have an `await` here. What we get instead is an async sequence called
> `stream`, which means we can then loop over it and assign all the outputs to our itinerary, which
> includes all these options [optionals]. So we say `try await partialResponse in stream`, and we can
> extract it using `partialResponse.content` where you'll get a snapshot every time of whatever has
> been generated at that point in time.**"

**Three precise facts:**
1. `streamResponse(to:generating:)` is **not `async`** — it *returns* an `AsyncSequence` synchronously.
2. Each element has a **`.content`** property of type `T.PartiallyGenerated`.
3. Each `.content` is a **complete snapshot** of everything generated so far — NOT a delta/token. This
   is exactly why Apple calls it **"snapshot streaming"** `[241:L1]`.

### 4.3 Views must unwrap `[205:L636-666]`

> "Since partially generated fields are **optionals**, we can use **`if let` statements** to safely
> unwrap these options."

```swift
// Views/ItineraryView.swift  (RECONSTRUCTED)
struct ItineraryView: View {
    let landmark: Landmark
    let itinerary: Itinerary.PartiallyGenerated

    var body: some View {
        ScrollView {
            if let title = itinerary.title {
                Text(title)
            }
            if let description = itinerary.description {
                Text(description)
            }
            if let rationale = itinerary.rationale {
                Text(rationale)
            }
            if let days = itinerary.days {
                ForEach(days) { day in
                    DayView(dayPlan: day)
                }
            }
        }
    }
}

struct DayView: View {
    let dayPlan: DayPlan.PartiallyGenerated
    // … same if-let treatment for title / subtitle / destination / activities
}
```

> "**you have to do the same for every single property**" `[205:L668]` — the presenter gives up doing it
> by hand and pastes the completed file from the guide `[205:L661-666]`.

### Chapter 4 UX payoff (verbatim, `[205:L675-676]`)

> "Unlike previously where it was an async call, now we are able to **stream responses as it is being
> generated. This has great user experience because someone using the app can start consuming this
> content even before all of the itinerary has been loaded.**"

---

## 3.5 CHAPTER 5 — Tool calling

### The tool-calling loop (verbatim narration of the diagram, `[205:L684-695]`)

> "In addition to what you provide to the prompt the model brings its own core knowledge from its
> training data but remember **the model is built into the OS and its knowledge is frozen in time**. So
> for example, if you ask it about **weather in Cupertino right now**, there's no way for it to know
> what that information is. To handle cases where you need **real time or dynamic data**, the framework
> supports tool calling."

Steps, verbatim:
1. "We have a **session transcript**."
2. "If you provided tools to the session, **the session will present the tool definition to the model
   along with the instructions**."
3. "the prompt tells the model which destination we want to visit."
4. "**if the model decides that calling a tool can enhance the response, it will produce one or more
   tool calls**. In this example, the model produces **two tool calls, querying restaurants and
   hotels**."
5. "At this phase, **the Foundation Models Framework will automatically call the code you wrote for
   these tools.**"
6. "**The framework then automatically inserts the tool outputs back into the session transcript.**"
7. "Finally, **the model will incorporate the tool output and everything else in the transcript into the
   final response.**"

### 🔑 Determinism via greedy sampling (verbatim, `[205:L696-702]`)

> "As we've seen so far, **the model can be very creative, often giving a slightly different itinerary
> each time we make a request. While this randomness is great for creativity, it can be a challenge
> when we need predictable [output]. For an advanced feature like tool calling, especially when testing
> and debugging, we need to ensure that the model behaves consistently. We want to guarantee that it
> will call our tool when we expect it to. To achieve this, we are going to make another small change
> to our request using generation options API to use greedy sampling. Greedy sampling tells the model
> to stop being creative and to always pick the most obvious next token. This makes the model's output
> deterministic. For our app, this ensures that the model will reliably call our tool every single
> time.**"

```swift
options: GenerationOptions(sampling: .greedy)
```
> "**By default, it does random sampling.**" `[205:L836-837]`

### 5.1 `FindPointsOfInterestTool` — full reconstruction

**RECONSTRUCTED** from `[205:L711-752]` (the presenter narrates each member as he pastes it):

```swift
// ViewModels/FindPointsOfInterestTool.swift  — RECONSTRUCTED from [205:L711-752]
import FoundationModels

final class FindPointsOfInterestTool: Tool {
    let name = "findPointsOfInterest"
    let description = "Finds points of interest for a landmark."

    let landmark: Landmark

    init(landmark: Landmark) {
        self.landmark = landmark
    }

    @Generable
    enum Category: String, CaseIterable {
        case hotel
        case restaurant
    }

    @Generable
    struct Arguments {
        @Guide(description: "This is the type of destination to look for.")
        let pointOfInterest: Category
    }

    func call(arguments: Arguments) async throws -> ToolOutput {
        let results = await getSuggestions(category: arguments.pointOfInterest)
        return ToolOutput("\(results)")     // "insert this result as a string output"
    }

    private func getSuggestions(category: Category) async -> [String] {
        switch category {
        case .restaurant:
            return ["Restaurant 1", "Restaurant 2", "Restaurant 3"]
        case .hotel:
            return ["Hotel 1", "Hotel 2", "Hotel 3"]
        }
    }
}
```

Narration per member:
- "a **class** called `FindPointsOfInterestTool` that **conforms to the `Tool` protocol**, which means
  we have to define a few properties" `[205:L713]`
- "**we provide our tool with a `name` which is 'find points of interest' and a `description` which is
  'find points of interest for a landmark'. This is critical for the model to understand when to invoke
  this tool. So it will use the name and the description to determine when to invoke this tool.**"
  `[205:L716-719]`
- "define the **categories** that the tool can search for… by introducing this **`@Generable` enum**. So
  the `Category` is an enum that includes **hotels and restaurants. This can of course include other
  cases like museums or campgrounds and others.**" `[205:L721-723]`
- "the `Arguments` struct, I have a property here that says **`let pointOfInterest`** and it is of type
  `Category`… and we also provide a **guide**. The guide has a description that says '**this is the type
  of destination to look for**.'" `[205:L727-729]`
- **"So this argument is the contract between the tool and the model. When the model wants to invoke
  the tool, it will pass this argument to the tool."** `[205:L730-731]`
- "`call` … **This function is the heart of our tool. It receives the arguments, performs an action, and
  returns an output that gets added back into the session's transcript for the model to see and use.**"
  `[205:L734-735]`
- "**`let results = await getSuggestions(...)`** … the results will be part of the output here, which
  you can then, as you see in the **`return` statement**, we can **insert this result as a string
  output** back to be provided back to the model." `[205:L739-743]`
- "within `getSuggestions`, I have a **switch block** which takes in a category and then if it's a
  **restaurant**, it can return **restaurant1, restaurant2 or restaurant3**. Similarly, if it's a
  **hotel**… **hotel one, hotel two, or hotel three**." `[205:L749-750]`
- **"Now, these are, for this demo, we are using hardcoded data. In a real app, this is where you would
  call APIs like MapKit or a server-side API to fetch real live data."** `[205:L751-752]`

⚠️ **UNVERIFIED details:**
- Exact `name` string (spoken as words, could be `"findPointsOfInterest"` or `"find_points_of_interest"`).
- Return type of `call`: the presenter says "insert this result **as a string output**". In the
  iOS 26 GA API this is `ToolOutput`; later revisions accept `String`/any `PromptRepresentable`.
  **Mark both possibilities in a guide.**
- `enum Category` raw type / `CaseIterable` conformance — my addition.
- Whether `Tool` requires `static let name`/`var name` vs `let name` — my reconstruction uses `let`.

### 5.2 Testing the tool in the Playground

**VERBATIM-ISH** `[205:L762-785]`:

```swift
#Playground {
    let landmark = ModelData.landmarks[0]          // → Sahara Desert
    let pointOfInterestTool = FindPointsOfInterestTool(landmark: landmark)

    let instructions = Instructions {
        "Your job is to create an itinerary for the user."
        "Always use the findPointsOfInterest tool to find hotels and restaurants in \(landmark.name)."
    }

    let session = LanguageModelSession(
        tools: [pointOfInterestTool],
        instructions: instructions
    )

    let prompt = Prompt {
        "Generate a 3-day itinerary to \(landmark.name)."
        "Here is an example of the desired format, but don't copy its content."
        Itinerary.exampleTripToJapan
    }

    let response = try await session.respond(
        to: prompt,
        generating: Itinerary.self,
        options: GenerationOptions(sampling: .greedy)
    )
}
```

Narration:
- 🔑 **"a neat feature of playground is that it has access to all the data structures in your Xcode
  project — without having to build the app."** `[205:L764-765]`
- "`ModelData.landmark[s][0]` which means I'm going to access one of those landmarks… specifically we
  are going to access **the first landmark and if you recall that is Sahara Desert**." `[205:L766]`
- 🔑 "There are **two minor code changes** if you look carefully. **One, it's no longer a string but
  `Instructions` builder — similar to prompt builder — wherein we pass in a closure and provide our
  instructions.** And **the second key change you'll notice, very important for tool calling**, is we
  say '**always use the findPointsOfInterest tool to find hotels and restaurants in this landmark**'.
  **Now this instruction is telling the model that it must invoke this tool in order to get the points
  of interest response.**" `[205:L771-774]`
- "we do introduce a new argument called **`tools`**. Here `tools` can be **an array of tools**… **Since
  it's an array, you can provide multiple tools so the model can reason about your prompts and
  instructions and decide which tool to call when.**" `[205:L776-779]`

**→ `InstructionsBuilder` exists as a peer of `PromptBuilder`.** Both are result builders taking
closures; both accept string literals *and* `@Generable` instances.

### 5.3 Reading the transcript — what tool calling looks like inside

`[205:L796-815]`. The presenter assigns `let inspectSession = session` to inspect it in the canvas.

> "you see **`tools`. It has one tool that we provided.** And if you look at **`transcript`, it has
> **six elements** in this `entries`."

The six entries, in order (verbatim `[205:L805-813]`):
1. **instructions** — "which is **always the very first entry in the transcript**"
2. **prompt** — "our initial request"
3. **tool calls** — "**The model autonomously decided that it needs to call our tool.**"
4. + 5. **tool outputs** — "**The framework executed our tool and inserted these tool outputs back into
   the transcript.**"
6. **response** — "**The model synthesized the original prompt, the tool output data to generate this
   final response.**"

> "**There are two tool calls here because we are requesting for both restaurants as well as hotels.
> And you'll see this under the tool calls. So there's a request for a restaurant and a hotel.**"
> `[205:L813-815]`

⚠️ **Arithmetic note:** 6 entries with 2 tool calls implies the layout is
`instructions, prompt, toolCalls(×2 in ONE entry), toolOutput, toolOutput, response`
— i.e. **`.toolCalls` is a single transcript entry holding an array of calls, while each tool output
is its own entry.** This is a reconstruction from the count; worth verifying against
`Transcript.Entry` in a guide.

### Observed output showing tool data woven in `[205:L791-795]`

> under `activity 1` description: "*Enjoy a traditional Moroccan dinner at **restaurant 1**.*"
> title: "*Dine-in at **restaurant 1***"; activity 2 title: "*Stay in **hotel 1** and unwind at
> **hotel 1***."
>
> "**This is the output of the tool that is being inserted into the output of the model.** So the model
> took in a prompt[,] instructions, the landmark name, invoke[d] the tool, got back the hotel and
> restaurant names and inserted it back to the transcript and generated this response."

### 5.4 App integration `[205:L825-842]`

Three changes:
1. Update instructions to add the "always use the tool" sentence.
2. Create the tool instance and pass `tools: [pointOfInterestTool]` to `LanguageModelSession`.
3. Add `options: GenerationOptions(sampling: .greedy)` to the `streamResponse` call.

```swift
// RECONSTRUCTED — ItineraryGenerator after Chapter 5
let stream = session.streamResponse(
    to: prompt,
    generating: Itinerary.self,
    options: GenerationOptions(sampling: .greedy)
)
```

### Chapter 5 recap (verbatim, `[205:L857-860]`)
> "we gave the model powers with tool calling. We discussed a custom tool with **its own arguments and
> `call` function**. We learned **how to provide the tool to the language model session**, and
> **importantly, how to instruct the model on when and how to use the tool.**"

---

## 3.6 CHAPTER 6 — Performance: Instruments, prewarming, schema exclusion

### 6.0 Profiling with the Foundation Models Instrument `[205:L866-902]`

Exact UI steps:
1. **Long-press the Run button** in Xcode → menu shows **Run / Test / Profile / Analyze** → click
   **Profile**. "What this does is it'll build the app and then launch up Xcode Instruments."
   `[205:L869-872]`
2. In Instruments choose the **Blank template** `[205:L875]`.
3. Click the **`+`** symbol and **search for "foundation models"** to add the instrument `[205:L875]`.
4. Click **record**, exercise the app, **stop**.

**Tracks in the Foundation Models instrument (2025 version), verbatim `[205:L886-891]`:**

| Track | What it shows |
|---|---|
| **Response** | "**The blue bar here represents [the] entire session.** So this is ever since the user clicks on generate itinerary, we create a session and the model takes in the instructions, prompts and generates output." |
| **Asset loading** | "once the session starts, **there is a little bit of a delay and then the models are loaded here, the model assets**, which means all this time from the start of the session all the way to end of loading the model, **the model is not generating any responses** and roughly looks like this is about **700 milliseconds, which is almost a full second**" |
| *(third track)* | "**this is where you see that the first token is generated**, which means it **waits for all the models to be loaded and then it starts the token generation process**, starting with the first token" |

**Bottom detail pane — "inference" section** `[205:L895-901]`:
> "you will see here that there is **max token count**. And we see here that this currently amounts to
> **1044**. And **this token count includes everything we've added into the session. This includes your
> instructions, your prompts, your tools. It includes the generables with the itinerary, all of it.**
> …**the number of tokens has an implication on the model's performance.**"

**Two identified bottlenecks:**
1. ~700 ms of asset loading blocking first token.
2. Max token count 1044 (instructions + prompt + tool definitions + Generable schema).

### 6.1 Prewarming

Rationale (verbatim, `[205:L904-909]`):
> "**If you recall, when we call `session.respond`, the OS will load the model if it's not already in
> memory. Prewarming can give your session a head start by loading the model before you even make a
> request.** In our app, **when someone taps on the landmark, it's pretty likely that they are going to
> make a request soon. We can pre-warm before they press the generate itinerary button** to proactively
> load the model. **By the time they finish reading the description, our model will be ready to go.**"

**VERBATIM-ISH** `[205:L932-941]`:

```swift
// ViewModels/ItineraryGenerator.swift
func prewarmModel() {
    session.prewarm()
}
```

…and the enhanced form:

```swift
func prewarmModel() {
    session.prewarm(promptPrefix: Prompt {
        "Generate a 3-day itinerary to \(landmark.name)."
    })
}
```

> "**If you ahead of time know what the prompt is going to be, you can also use a prompt prefix**…
> **inside [the] `session.prewarm` function, there is an optional argument called `promptPrefix` where
> you can provide a prompt so the model has knowledge of the prompt that the user might provide and it
> can prewarm using this. So here we pass a prompt with a closure that says 'generate a three-day
> itinerary to `landmark.name`'. This can further improve performance.**" `[205:L937-942]`

Call site `[205:L943-948]` — `Views/LandmarkTripView.swift`:

```swift
.task {
    let generator = ItineraryGenerator(landmark: landmark)
    self.itineraryGenerator = generator
    generator.prewarmModel()        // "as simple as calling the generator.prewarmModel function"
}
```

⚠️ `prewarm()` is **not** `async`/`throws` in this usage — it is fire-and-forget.

### 6.2 `includeSchemaInPrompt: false`

Rationale (verbatim, `[205:L910-913]`):
> "Recall that **generable structs provided to the model can help generate structured outputs, but this
> comes at the cost of increased token count, which affects initial processing time**. Also recall that
> in Chapter 3, we passed an example itinerary called `exampleTripToJapan`. **Since our instructions
> includes this full example of the generable schema, we can often exclude the schema definition itself
> from the [prompt], which saves space and can speed up the model.**"

Restated `[205:L918-921]`:
> "because **our one-shot example is quite detailed, the full schema definition in the prompt is
> redundant. We can remove it by setting `includeSchemaInPrompt` to `false`.** In our `streamResponse`
> call, we'll make this change. **This will significantly reduce our input token count.**"

**VERBATIM-ISH** final `streamResponse`:

```swift
let stream = session.streamResponse(
    to: prompt,
    generating: Itinerary.self,
    includeSchemaInPrompt: false,
    options: GenerationOptions(sampling: .greedy)
)
```

⚠️ **Parameter ordering:** the presenter describes adding `includeSchemaInPrompt` *after* prompt,
generating, and options `[205:L959]`. The real signature is
`streamResponse(to:generating:includeSchemaInPrompt:options:)` — I've placed it there.
**Mark as reconstruction of ordering.**

### 6.3 Measured results (verbatim, `[205:L979-987]`)

> "**The very first thing you should notice is that asset loading happened well before the session
> started thanks to our pre-warm function.** So we loaded this asset at this point when the user clicked
> on the detail view we called the pre-warm method by adding the pre-warm function in the task **which
> means by the time the user used to read the title and description, the model was already loaded and
> ready.** And if you take a closer look at the start of the session here, you'll see that **the output
> starts generating almost as soon as the session started.**"

> "down here under inference you'll see **the maximum token count has dropped to 700. Previously it was
> 1000** so we have dropped the maximum token count to 700 **by excluding the schema from the prompt.**
> Now this also means that **the model is able to much quickly process the initial token and start
> generating responses a lot quicker.**"

**Hard numbers to quote in a guide:**
| Metric | Before | After |
|---|---|---|
| Max token count | **1044** (`[205:L897]`) — later rounded to "1000" | **700** |
| Asset-load position | ~700 ms *inside* the session, blocking first token | *before* the session begins |

### 🔑 The safety condition on `includeSchemaInPrompt: false`

`includeSchemaInPrompt: false` is only safe **because a fully-populated `@Generable` instance is
already embedded in the prompt** (chapter 3's `Itinerary.exampleTripToJapan`), which carries the schema
implicitly `[205:L570-572]`, `[205:L960]`. **Turning it off without a one-shot example is a footgun.**
*(Transcript typo at `[205:L960]`: "we are already passing the example trip to Japan in **instruments**"
— clearly "in **instructions**".)*

### 6.4 Final recap and what was NOT covered `[205:L1002-1004]`

> "we've covered a lot today from basic text generation to guided generation, streaming, tool calling,
> and performance optimizations, but there's still more to explore. **We didn't have time to cover some
> advanced topics such as training custom model adapters, dynamic runtime schemas, or diving into
> guardrails and error handling.**"

→ **Three named gaps in the code-along: adapters, dynamic runtime schemas, guardrails/error handling.**
These are guide-topic candidates.

> "**The completed sample project from today, including [a] few additional features is available for
> download in the Foundation Models Framework documentation.**" `[205:L1008]`

Support channel `[205:L1005-1007]`: developer forums at `developer.apple.com/forums`.

---

# PART 4 — Cross-checks against local material

## 4.1 `docs/` — NO overlap

`/Volumes/ExtStor/FM and MLX and CoreAI/docs/` contains only **7 files**, all Core AI / Speech:
```
Compiling Core AI models ahead of time.md
Run AI models in your app on Apple silicon.md
Integrating on-device AI models in your app with Core AI.md
Bringing advanced speech-to-text capabilities to your app.md
Managing model specialization and caching.md
Recognizing speech in live audio.md
```
**There is NO Foundation Models documentation in `docs/`.** No cross-check was possible from that
folder. (Flagged for the orchestrator: the FM docs corpus is missing and should be fetched.)

## 4.2 `repos/apple__python-apple-fm-sdk` — strong corroboration + 4 deltas

Covered in §2.3 above. Summary of the four notable deltas:
1. README says **macOS 26.0+**, contradicting the "new on macOS 27" framing.
2. README adds a requirement the talk omits: **you must open Xcode and agree to the Xcode/Apple SDKs
   agreement**.
3. README's feature list **does not mention tool calling**; the transcript does.
4. Transcript says "`fm.respond`"; README shows **`session.respond`** (README wins).

Extra facts only in the repo (not in either transcript):
- Repo layout includes `foundation-models-c/` (a C shim), `build_backend.py`, `bin/`, `tests/`,
  `.swift-format` → **the Python SDK is a Swift/C-backed native extension**, not pure Python.
- `examples/`: `simple_inference.py`, `streaming_example.py`, `transcript_processing.py`.
- README explicitly points at safety docs: *"Improving the safety of generative model output"* and
  *"Human Interface Guidelines on Generative AI"* (README.md:20-23), with the line:
  **"Keep in mind that it's your responsibility to design AI experiences with care."**
- Copyright line: "Copyright (C) **2026** Apple Inc."

## 4.3 `forums/machine-learning-and-ai-foundation-models.txt` — confirms/extends 8 items

| Item | Confirms/extends |
|---|---|
| `LanguageModelSession(model: PrivateCloudComputeLanguageModel())` | ✅ confirms exact type + `model:` label from `[241:L29-34]` |
| `SpotlightSearchTool()` + `LanguageModelSession(tools: [tool])` | ✅ gives the concrete name for `[241:L63]`'s "search tool powered by Spotlight" |
| `GenerationOptions(toolCallingMode: .required)` | ➕ **new 2026 option NOT in any of my three transcripts** |
| `LanguageModelSession(tools: [tool]) { instructions }` | ➕ trailing `@InstructionsBuilder` closure on the init |
| `SystemLanguageModel(guardrails: .permissiveContentTransformations)` | ➕ **guardrails configuration on the model initializer**, with the caveat quoted by the developer: *"`.permissiveContentTransformations` does not apply to Generable"* |
| `tokenCount(for:)` + `exceededContextWindowSize` | ✅ concrete names for the iOS 26.4 context APIs in `[241:L14-15]` |
| `ChatCompletionsLanguageModel` w/ private `buildURLRequest(for:)` | ✅ confirms the utilities package's "language model that can interface with servers using the Chat Completions standard" `[241:L130]`. **Bug filed:** it hardcodes `"v1"` detection: `let isVersioned = baseURL.pathComponents.contains("v1")` then `let endpoint = isVersioned ? "/chat/completions" : "/v1/chat/completions"` — breaks non-`v1` API versions. |
| `SkillActivation` in `github.com/apple/foundation-models-utilities` | ✅ confirms "skill API for procedural knowledge loading" `[241:L130]` and gives the **repo URL**. Build failures reported on Xcode 26 beta. |

Additional forum-only intel relevant to `fm-core`:
- **Adapters:** `xcrun ba-package foundation-models package --adapter-path <name>.fmadapter --asset-pack-id <id>` — packaging an adapter as a Background Assets pack; failure mode **`compatibleAdapterNotFound`** when delivered via TestFlight-hosted managed asset pack (works via local `fileURL:`). Adapters were *not* covered in any of my three transcripts (explicitly deferred at `[205:L1003]`).
- **New error type:** thread 836673 reports on iOS 27 beta 2 a **`LanguageModelError`** with *"The model refused to answer" / "May contain sensitive content"* — **distinct from `GenerationError.guardrailViolation`**. Regression vs iOS 26.x for health-summary prompts. This is a *model-level* refusal, not a guardrail. **Important taxonomy point:** `GenerationError.guardrailViolation` ≠ `LanguageModelError` refusal.
- **`com.apple.SensitiveContentAnalysisML error 15`** on Xcode 27 beta 2 for a trivial `#Playground` prompt ("List all states of USA").
- **Availability coupling to Siri (iOS 27 beta 1):** *"it looks like the user must enable either 'Siri'/'Hey Siri' or 'Press Side Button for Siri' in iOS settings for `SystemLanguageModel.default.availability` to report true. Otherwise, it returns `.appleIntelligenceNotEnabled`."* Same reported on macOS beta 2 (thread 836760). **Real behavioural gotcha layered on top of the `205` availability chapter.**
- **No `UIRequiredDeviceCapabilities` equivalent for FM** — thread 836810 asks how to prevent installs on non-AI devices for AI-first apps; no Apple answer in the feed. Open App Store distribution question.
- **`MLXFoundationModels` module** referenced in wwdc2026-339's code samples but developers report it is **not findable** in any MLX branch (thread 836264). Ties to `[241:L47]`'s `MLXLanguageModel`.

## 4.4 Sibling transcripts (grep-level only — other agents' scope)

- `wwdc2026-242.txt` (dynamic profiles deep dive) L12-13, L86, L137 — confirms utilities is an
  **open source Swift package**, that **modifiers** live there, and that it houses a **`Skills` type**
  for "procedural context loading".
- `wwdc2026-339.txt` (bring an LLM provider) L22 — "if you want to try the latest open source models,
  simply **pass in a model ID**, and let the framework handle the rest"; L42 — "**because the Foundation
  Models framework is being released as open source, your package could also be useful to developers
  who deploy Swift on their servers, so consider supporting Linux too**."

---

# PART 5 — Consolidated gotchas / footguns / version gates

## Version & hardware gates
1. **`fm` CLI: macOS 27 only**, pre-installed `[334:L15,L35]`.
2. **Python SDK: macOS 26.0+**, Python 3.10+, Xcode 26.0+ (and you must accept the Xcode SDK agreement in the Xcode app), Apple Silicon, Apple Intelligence on. (repo README vs `[334:L88-90]`)
3. **Evaluations framework: Xcode 27** `[334:L121]`.
4. **Context-size + token-counting APIs: iOS 26.4** (not 27) `[241:L15]`.
5. **Guardrail false-positive reduction: iOS 26.4**, more in iOS 27 `[241:L18-19]`.
6. **watchOS 27**: FM available via PCC `[241:L41]`; beta 2 has a `CoreImage` swiftinterface build break.
7. **Code-along baseline**: Apple Silicon Mac + macOS Tahoe + Xcode 26; or iPhone on iOS 26 `[205:L55-57]`.
8. **PCC eligibility: < 2 million first-time (lifetime) downloads** for free cloud API `[241:L42]`.

## Runtime footguns
9. **First `respond` is slow** — model must load into memory `[205:L166-170]`. Fix: `session.prewarm()`, ideally with `promptPrefix:`.
10. **`includeSchemaInPrompt: false` is only safe with a one-shot `@Generable` instance in the prompt** — otherwise the model has no schema at all `[205:L913,L960]`.
11. **`@Guide(.anyOf(...))` vs prompt vocabulary mismatch** — asking for "Paris" when the guide restricts to app landmarks produces a mismatch `[205:L432-435]`.
12. **Never interpolate user input into `instructions`** — prompt-injection defense; instructions outrank prompts `[205:L196-197]`.
13. **Larger images = more tokens + more latency**, even though any size/aspect ratio is accepted `[241:L26-27]`.
14. **Token budget counts EVERYTHING**: instructions + prompt + tool definitions + Generable schema `[205:L898-900]`.
15. **More-detailed prompts are not monotonically better** — Apple's own Python case study shows the most detailed prompt caused *more generation errors* (context-window exhaustion) and *more missed expected items*, while the least detailed caused *more hallucinations* `[334:L148-152]`.
16. **Non-determinism by default** — "By default, it does random sampling" `[205:L836-837]`. Use `GenerationOptions(sampling: .greedy)` for reproducible tests, especially when asserting tool invocation.
17. **A tool won't be called unless you tell the model to call it** — the code-along's instructions include a literal "Always use the `findPointsOfInterest` tool…" sentence `[205:L773-774]`; and forums show devs resorting to `toolCallingMode: .required`.
18. **All `PartiallyGenerated` properties are optional and must be `if let`-unwrapped in EVERY view, including nested types** `[205:L636-668]`.
19. **`streamResponse` is not `async`** — don't `await` the call itself, only the `for try await` loop `[205:L627-628]`.
20. **Dynamic profiles + privacy boundary**: switching a profile's model mid-session carries the accumulated transcript to the new backend. "consider privacy boundaries, model capabilities, and cost" `[241:L103]`.
21. **Third-party models**: never ship keys in the binary; OAuth + Keychain `[241:L52-53]`.
22. **PCC quota API is coarse** (reached / below / approaching) — no numeric budget (forums 835974).
23. **Availability may require Siri to be enabled** on iOS 27 / macOS 27 betas, otherwise `.appleIntelligenceNotEnabled` (forums 835211, 836760).
24. **Model refusals ≠ guardrail violations**: iOS 27 betas surface `LanguageModelError` ("The model refused to answer"), which is *not* `GenerationError.guardrailViolation` (forums 836673). Handle both.
25. **`utilities` package is explicitly "emerging and experimental"** and updates out-of-band with the OS `[241:L5]`.
26. **`ChatCompletionsLanguageModel` hardcodes `v1` URL detection** — breaks non-v1 OpenAI-compatible endpoints (forums 838444).
27. **FM image input is unreliable for bounding boxes / spatial coordinates** (forums 838613).

## Testing / tooling
28. **Simulate unavailability without extra devices**: Edit Scheme → **"Simulated Foundation Models availability"** `[205:L253-257]`.
29. **`#Playground` can appear multiple times in one file**; each becomes a **canvas tab** `[205:L211,L216]`.
30. **`#Playground` sees your whole project's types without building/running the app** `[205:L764-765]`.
31. **Model feedback**: thumbs-up/down in the `#Playground` canvas, macOS/iOS 26 Beta 4+ (forums 791250, `[205:L177]`).
32. **Profile with Instruments**: long-press Run → Profile → Blank template → `+` → "Foundation Models". Tracks: Response / Asset Loading / first-token; detail pane has **max token count** `[205:L869-901]`.

---

# PART 6 — Source inventory (everything I actually opened this session)

**Read in full (assigned):**
1. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-241.txt` (140 lines)
2. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-334.txt` (171 lines)
3. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/meet-with-apple-205.txt` (1013 lines)

**Read in full (cross-check):**
4. `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__python-apple-fm-sdk/README.md` (138 lines)

**Read substantially (cross-check):**
5. `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-and-ai-foundation-models.txt`
   (full RSS feed, ~15 threads, lines 1-420)

**Directory listings / greps only:**
6. `/Volumes/ExtStor/FM and MLX and CoreAI/docs/` (7 files listed — all Core AI/Speech, none FM)
7. `/Volumes/ExtStor/FM and MLX and CoreAI/repos/` (16 repos listed)
8. `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__python-apple-fm-sdk/` (tree + `examples/`, `docs/`)
9. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/` — first 300 chars of all 17 transcripts (for cross-link mapping)
10. grep hits in `transcripts/wwdc2026-242.txt` (L12,13,86,137) and `transcripts/wwdc2026-339.txt` (L22,42,175)

**Transcript → topic map built this session** (for cross-linking, from first-300-chars scan):

| File | Topic |
|---|---|
| `wwdc2026-232` | MLX agentic workflows on Mac (Angelos) |
| `wwdc2026-241` | **What's new in Foundation Models** ← mine |
| `wwdc2026-242` | Dynamic profiles / agentic FM (Erik, Oliver) |
| `wwdc2026-243` | FM + Instruments debugging (Erik) |
| `wwdc2026-246` | FM + Core Spotlight search (Jennifer) |
| `wwdc2026-298` | Meet the Evaluations framework (Yada, Rob) |
| `wwdc2026-299` | Advanced Evaluations (Ada, Kyle) |
| `wwdc2026-319` | **Private Cloud Compute** server LLM (Louis) |
| `wwdc2026-324` | Meet Core AI (Ben) |
| `wwdc2026-325` | Core AI on Apple Silicon (Sachin, Nicole) |
| `wwdc2026-326` | Core AI app features (Carina) |
| `wwdc2026-330` | Metal tensors / TensorOps (Shiyao) |
| `wwdc2026-334` | **FM on macOS: `fm` CLI + Python SDK** ← mine |
| `wwdc2026-335` | Evaluations for feature improvement (Marcus) |
| `wwdc2026-339` | **Bring an LLM provider to FM** (Christopher Webb) |
| `meet-with-apple-205` | **FM Framework Code-Along** ← mine |

---

# PART 7 — Open questions / UNVERIFIED

1. **Image attachment type name.** `[241:L23]` says "insert an **image attachment**" — concrete Swift type (`ImageAttachment`? `Prompt.Image`?) never stated. Needs the image-understanding session or FM docs.
2. **`contextOptions` type name and `reasoningLevel` cases.** Only "deep reasoning" is named `[241:L37]`. Are there `.minimal`/`.medium`/`.deep`? Is `contextOptions` a struct or an enum?
3. **`usage` property shape.** Confirmed to exist on sessions AND responses `[241:L55]`, with cached-input and reasoning-token facets — no property names.
4. **`DynamicProfile` / `Profile` exact API.** `body` returns "a `Profile`" — is it `some Profile` (protocol + result builder) or a concrete struct? What is the `LanguageModelSession` initializer label (`profile:`?)? Modifier names (`.model(_:)`, `.reasoningLevel(_:)`) are reconstructed. → `wwdc2026-242.txt` agent should resolve.
5. **`fm` CLI flag spellings.** Only semantic option names spoken ("the model option", "the image option", "the schema option", "the help option"). Long/short forms unknown.
6. **`fm schema object` grammar.** Never shown. This is the single biggest gap in the `fm` story.
7. **Full `fm` subcommand list.** "and more" `[334:L39]` — `respond`, `chat`, `schema` are the only three named.
8. **`fm chat` slash commands beyond `/model` and `/save`.** "a number of commands" `[334:L43]`.
9. **`Tool.call` return type.** "insert this result as a **string output**" `[205:L743]` — `ToolOutput` vs `String` vs generic `PromptRepresentable`? May have changed between iOS 26 and 27.
10. **`Tool` protocol required members.** `name`, `description`, `Arguments`, `call(arguments:)` are confirmed; is `Arguments` an associatedtype? Is there an `includesSchemaInInstructions` knob?
11. **`@Guide(.anyOf(...))`** — exact spelling, and whether other guide constraints exist (`.count(...)`, `.pattern(...)`, ranges).
12. **`Transcript.Entry` cases.** Reconstructed from a count of 6 with 2 tool calls; need the actual enum (`.instructions`, `.prompt`, `.toolCalls`, `.toolOutput`, `.response`?).
13. **`streamResponse` parameter order** with `includeSchemaInPrompt`.
14. **Does `respond` also take `includeSchemaInPrompt`?** Only demonstrated on `streamResponse` `[205:L959]`.
15. **Context window sizes.** PCC = 32,000 `[241:L31]`. **On-device context window size is never stated** in any of my three transcripts — and `[241:L16]` implies it *varies by hardware*. Needs the context-size API + docs.
16. **`SystemLanguageModel(guardrails:)`** — full set of guardrail options; forums only name `.permissiveContentTransformations`, plus the caveat that it "does not apply to Generable".
17. **`GenerationOptions` full surface.** Confirmed: `sampling: .greedy` `[205:L785]`, `toolCallingMode: .required` (forums). Others (temperature, maximumResponseTokens) unverified in this session.
18. **`CoreAILanguageModel` / `MLXLanguageModel` package names & repos.** `[241:L47]` names the types; forums show devs unable to find `MLXFoundationModels`.
19. **Anthropic / Google Swift package names and URLs.** `[241:L48]` — not given.
20. **Where the open-sourced FM framework lives** (repo URL). Only `github.com/apple/foundation-models-utilities` surfaced, via forums.
21. **Python SDK tool calling** — claimed in `[334:L95]`, absent from the README feature list. Which is current?
22. **Does the Python SDK reach PCC**, or on-device only? `[241:L123]` says "the very same **on-device** model"; `334` never mentions PCC from Python. Likely **on-device only** — needs confirmation.
23. **Adapters.** Explicitly deferred by the code-along `[205:L1003]`. Only forum evidence: `.fmadapter` files, `xcrun ba-package foundation-models package --adapter-path … --asset-pack-id …`, `compatibleAdapterNotFound`.
24. **"Dynamic runtime schemas"** — named as an uncovered topic `[205:L1003]`; presumably `DynamicGenerationSchema`. Not covered anywhere I read.
25. **The "2027 release" phrasing** `[241:L3]` — Apple's internal naming, or transcription artifact?
26. **App Store gating for FM-required apps** — no `UIRequiredDeviceCapabilities` equivalent (forums 836810, unanswered).
