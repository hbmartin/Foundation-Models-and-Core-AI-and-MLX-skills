# Apple Developer Forums — Machine Learning & AI: Threads, Apple-Staff Answers, and Pain-Point Clusters

**Research agent notes. Captured 2026-07-27.**
**Scope:** the four local RSS captures in `/Volumes/ExtStor/FM and MLX and CoreAI/forums/` PLUS ~45 live thread fetches from
`developer.apple.com/forums/thread/<id>` and the topic listing pages (8 pages of Foundation Models threads).

Everything below is grounded in a source read in this session. Where a claim is *not* directly verified I mark it
**[UNVERIFIED]**. Apple-staff quotes are reproduced as fetched; the fetch layer converts HTML→markdown so wording of
prose replies is faithful but formatting (bold/italics) may vary slightly. Code blocks are verbatim.

---

## 0. TL;DR — the ten highest-value facts pulled out of these forums

1. **Custom LoRA adapters are DEAD as of OS 27.** Two independent Apple-staff statements. Adapter Training Toolkit
   stops at 26.0.0.
2. **There are now two on-device models: `AFM 3 Core` and `AFM 3 Core Advanced`**, split by hardware tier — with an
   exact device list given by Apple staff.
3. **All on-device Apple Foundation Models are "powered by Core AI"** (direct Apple Frameworks Engineer quote).
4. **On-device context window is 4K (4096) tokens; PCC is 32K** (32K figure is community-sourced, see caveats).
5. **PCC eligibility = App Store Small Business Program + fewer than 2 million first-time app downloads + PCC
   entitlement.** Exceeding 2M → notified, 6 months to migrate.
6. **PCC does not work in the Simulator** (known issue 177684296, documented in iOS 27 release notes).
7. **Simulator runs the model by "punching out" to the host macOS**, so Xcode 27 SDK + macOS 26 host = weird errors.
   This is the single biggest source of phantom bug reports.
8. **`.anyOf` guide is confirmed-broken** (Apple staff reproduced it): it does not actually constrain generation.
9. **`SpotlightSearchTool`'s human-readable `description` and its generated `parameters` JSON Schema disagree**, so
   the tool is uninvokable by any non-Apple model. Confirmed "known issue" by DTS.
10. **New iOS 27 session APIs surfaced only in forum answers:** mutable `session.transcript`, `transcript.history`,
    `DynamicProfile` / `DynamicProfileModifier` (`onPrompt`, `onToolCall`, `historyTransform`, `toolCallingMode(_:)`),
    `summarizeHistory`, `CustomSegment`.

---

## 1. Source capture files (local)

| File | Lines | Feed title | Channel link |
|---|---|---|---|
| `forums/machine-learning-and-ai-foundation-models.txt` | 287 | **Foundation Models** | `https://developer.apple.com/forums/topics/machine-learning-and-ai/machine-learning-and-ai-foundation-models` |
| `forums/machine-learning-and-ai-topic-apple-intelligence.txt` | 211 | **Apple Intelligence** | `.../machine-learning-and-ai-topic-apple-intelligence` |
| `forums/machine-learning-and-ai-topic-evaluations.txt` | 30 | **Evaluations** | `.../machine-learning-and-ai-topic-evaluations` |
| `forums/machine-learning-topic-general.txt` | 223 | **General** | `.../machine-learning-topic-general` |

All four are **RSS 2.0 XML** (`<rss version="2.0">` with `xmlns:content`). Each `<item>` has
`<title>`, `<link>`, `<content:encoded>` (TRUNCATED with a trailing `...`), `<pubDate>`, `<author>`.
**Critical: the `content:encoded` bodies are cut off mid-sentence and contain no replies.** All Apple answers
below came from live fetches, not from these files.

Feed descriptions (verbatim from the XML):

- Foundation Models: *"Discuss the Foundation Models framework which provides access to Apple's on-device large
  language model that powers Apple Intelligence to help you perform intelligent tasks specific to your app."*
- Apple Intelligence: *"Apple Intelligence is the personal intelligence system that puts powerful generative models
  right at the core of your iPhone, iPad, and Mac and powers incredible new features to help users communicate, work,
  and express themselves."*
- Evaluations: *"Discuss how to use Evaluations to design and run evaluation suites for LLM-based features in your apps."*
- General: *"Explore the power of machine learning within apps. Discuss integrating machine learning features, share
  best practices, and explore the possibilities for your app."*

---

## 2. Complete thread enumeration

### 2.1 Foundation Models topic — page 1 (= the RSS capture, newest first)

| # | Thread ID | Title | Author | pubDate | Replies |
|---|---|---|---|---|---|
| 1 | 791250 | Provide actionable feedback for the Foundation Models framework and the on-device LLM | **DTS Engineer (Apple)** | 2025-07-01 | 0 (locked, sticky) |
| 2 | 838904 | Use of `SpotlightSearchTool()` returns "Model Catalog error: Error Domain=com.apple.UnifiedAssetFramework Code=5000", although model is available | BlueFox123 | 2026-07-22 | 2 |
| 3 | 838613 | Foundation Models, image input and locating things within an image | jaywardell | 2026-07-20 | 1 |
| 4 | 838444 | Issue: Inflexible API Versioning Logic in Foundation Models framework utilities | Stv-X | 2026-07-18 | 2 |
| 5 | 835974 | More Detailed Quota Usage for PCC | Enderlyn | 2026-06-24 | 2 |
| 6 | 835897 | I did well on iOS a decade ago. So - no foundation models for me? | Confused Vorlon | 2026-06-24 | 5 |
| 7 | 834149 | TTS Advanced Speech Generation: Expressive voices | juan.moya | 2026-06-12 | 1 |
| 8 | 834749 | Accessing Private Cloud Compute | lijiaxu | 2026-06-15 | 1 |
| 9 | 836285 | Sensitive Content Error When Using Foundation Models | azamsharp | 2026-06-28 | 2 |
| 10 | 829108 | Adapter Problem - `compatibleAdapterNotFound` | alex_und3r | 2026-06-04 | 6 |
| 11 | 836810 | Recommended App Store distribution strategy for apps that require Foundation Models | a_okano | 2026-07-03 | 5 |
| 12 | 837226 | SpotlightSearchTool Not Invoked, Console Error | Hunter | 2026-07-07 | 6 |
| 13 | 836760 | Foundation models tied to Siri in Mac OS beta 2 | Gil | 2026-07-02 | 1 |
| 14 | 836673 | Foundation Models: Model-level refusal regression on iOS 27 beta for health app prompts (not guardrailViolation) | rileygersh | 2026-07-01 | 1 |
| 15 | 834652 | Can any Apple Watch running WatchOS 27 access PCC via Foundation Models? | simonfromhelix | 2026-06-14 | 1 |
| 16 | 836264 | Bring an LLM provider to the Foundation Models, missing MLX dependencies | jorgevmendoza | 2026-06-27 | 2 |
| 17 | 835987 | FoundationModels Framework on watchOS 27 Beta 2 | arno_app | 2026-06-24 | 1 |
| 18 | 835927 | Feedback on Foundation Models context management wrapper | rickystone | 2026-06-24 | 1 |
| 19 | 835777 | Has something in FoundationModels guardrails changed recently? | jamalK | 2026-06-23 | 1 |
| 20 | 835165 | SkillActivation Framework Fails to Build in Xcode 26 When Using foundation-models-utilities | TheTravis | 2026-06-18 | 2 |
| 21 | 835211 | Why is `SystemLanguageModel.default.availability` tied to user enabling talk / press side button for Siri? | NSCruiser | 2026-06-18 | 0 |

### 2.2 Foundation Models topic — page 2 (mostly WWDC26 Foundation Models Q&A threads)

833761 Siri As Coding Agent · 833678 Custom vocabulary for speech and entity resolution ·
**788053 Guardrail configuration options?** · **833610 What is _the_ proper way to intercept tool calls modify them or
dynamically approve/reject them?** · **832910 Foundation Model Variation within the same iOS different hardware** ·
**831998 PrivateCloudComputeLanguageModel fails to respond** · **833716 Framework Boundaries** ·
**833614 Improved Guardrails Error Handling** · 833656 Confirmation, permissions, and reversibility for agentic
actions · **833651 Can the SpotlightSearchTool work with a custom model executor?** · 833655 RAG boundary: static
knowledge vs live data · **833658 LLM search using Core Spotlight** · 833595 Tool calling: App Intents vs server-side
orchestration · 833783 Image size, format, and background vs other VLMs · 833644 Visual Intelligence and screen/camera
understanding for third-party apps · 833635 Time Series Models · **833706 On Advanced Context Management** ·
**833657 Is AFM 3 Core a CoreAI model?** · **833692 Strict RAG implementation via .required tool calling and temp=0**

### 2.3 Foundation Models topic — page 3

**833650 Structured intents vs free-form queries** · 833712 Questions About Apple Foundation Models, Context Window
Limits and the New Core AI Framework · 833691 Disambiguation when multiple entities match · 833681 Siri without
opening the app · **833683 On Protocol Extensibility & Multi-Modal Data** · 833662 Privacy, personalization, and App
Store expectations · **833560 Summarization that must not hallucinate numbers** · **833575 Using FoundationModels
framework in Extensions** · 833668 On Agentic Testing & Accessibility · 833676 React Native + native AI bridge ·
833701 In-app text input vs system speech paths · **833666 On Performance & Backgrounding** · **833642 On-device model
capabilities, limits, and versioning** · 833696 Mixed languages and foreign proper nouns · 833661 Speech recognition
with large, dynamic vocabularies · 833653 Creating an in-universe AI computer in my app · 833623 RAG support ·
**833641 Guidance Around PCC** · **833626 Dynamic profile switching** · 833625 Hobbyist Eligibility for App Store
Small Business Program

### 2.4 Foundation Models topic — page 4

833630 The standalone Siri app and cross-surface continuity · **833627 Foundation Models framework — the unified API
for third-party cloud providers** · 833652 Hybrid assistant architecture (on-device model + server tools) ·
833628 Private Cloud Compute trust model across multiple cloud vendors · 833638 Spotlight semantic index & entity
schemas — privacy and dynamic/remote content · **833590 Clarifying the "Weight List"** · 833643 App Intents — exposing
conversational and agentic actions to Siri AI · 823423 backDeploy `SystemLanguageModel.tokenCount` · 833110 Approaching
Custom VST GUI Automation: Combining local Vision OCR with the new FoundationModels framework for screen-grounding ·
833002 Siri to be interoperable with Copilot's version control systems · 832868 Speech generation by the new Foundation
Model · 832555 Use different model in foundation model · **832534 SpotlightSearchTool arguments: description vs. JSON
Schema mismatch → "Failed to parse generated content"** · **831197 MLX, MLX LM, MLX LM Server -> Is there a bootstrap
repo?** · **831448 How to obtain more value out of a generic "FoundationModels.LanguageModelError error -1"** ·
**831404 Cannot pattern match LanguageModelError from a response stream** · **832033 Deployment & Entitlements** ·
**831314 Adapter Training Toolkit: updated version for OS 27?** · **830161 Foundation Models as part of OS**

### 2.5 Foundation Models topic — page 5

831215 Can FoundationModels Chat be used to explain 2025-2026 Foundation Models features and documentation? ·
**829539 Private Cloud Compute entitlement** · 816820 What Should the iOS Deployment Target Be Set to? ·
**823001 `SystemLanguageModel.Adapter` leaks ~100MB of irrecoverable APFS disk space per call** ·
**823148 Apple managed asset pack for FoundationModels adapter on Testflight does not download (statusUpdates silent)** ·
821602 26.4 Foundation Model rejects most topics · 821067 Unable to use FoundationModels in older app? ·
820798 Plenty of `LanguageModelSession.GenerationError.refusal` errors after 26.4 update ·
**820819 iOS 26.4: Regressions in Foundation Models** · **797271 Error: An unsupported language or locale was used** ·
818087 Two errors in debug: `com.apple.modelcatalog.catalog` sync and `nw_protocol_instance_set_output_handler` ·
817495 Apple Intelligence Naughty Naughty · 816926 Creating powerful, efficient, and maintainable applications ·
**817502 Handling exceedingContextWindowSizeError** · 816831 What Should the iOS Deployment Target Be? ·
816571 Xcode Playground and FoundationModels · 806779 Context window 90% of adapter model full after single user prompt ·
815121 Assert error breaking previews · 797724 Error with guardrailViolation and underlyingErrors ·
809497 Apple's PCC + Foundation Models

### 2.6 Foundation Models topic — page 6

798570 Error in Xcode console · 787445 Foundation Model Framework · **811620 Defining a Foundation Models Tool with
arguments determined at runtime** · **812501 Foundation Models: Is the `.anyOf` guide guaranteed to produce a valid
string?** · 810398 Feature Request: Allow Foundation Models in MessageFilter Extensions · 810783 Pre-inference AI
Safety Governor for FoundationModels (Swift, On-Device) · 811381 LanguageModelSession with multiple tools and
structured outpout · 810767 Deterministic AI Safety Governor for iOS — Seeking Feedback on App Review Approach ·
811714 Image understanding to on-device model · 802921 Foundation Models (Detected Content Likely to be Unsafe) Error ·
808765 Help with dates in Foundation Model custom Tool · 806542 FoundationModel, context length, and testing ·
807863 Computer Vision and Foundation Models · 807459 Is there an API that allows iOS app developers to leverage Apple
Foundation Models to authorize a user's Apple Intelligence extension, chatGPT login account? · 805048 Usage of
Foundation Model Framework · 807145 GenerationError -1 / 1026 · 805970 Training adapter, it won't call my tool ·
787736 Model Guardrails Too Restrictive? · **805378 Foundation Models unavailable for millions of users due to device
language restriction - Need per-app language override** · 805402 Defining instructions employing Content Tagging Model

### 2.7 Foundation Models topic — page 7 (of 8 total)

804444 Missing module `coremltools.libmilstoragepython` · 804366 Use apple private cloud model instead of local model ·
804363 Using `#Preview` with a PartialyGenerated model · 803614 Avoid hallucinations and information from trainning
data · 803444 Foundation Models inside of `DeviceActivityReport`? · 800238 How to Estimate Token Count Before Passing
Context to Apple's Foundation Model? · **803442 Does Foundation Models ever do off-device computation?** ·
802119 Xcode Version 26.0.1 (17A400) Model assets are unavailable · 802593 I Need some clarifications about
FoundationModels · 803258 Apple on-device AI models · 803040 How can I give my documents access to Model Foundation ·
802082 Code along with the Foundation Models framework · 787468 Foundation Models not working: "Model is unavailable"
error on iPad Pro M4 · 801504 Context Size Error But Size is Less Than Limit · 800031 Foundation Model Framework ·
799846 Foundational Model - Image as Input? Timeline · 797955 Model w/ Guardrails Disabled Still Frequently Refuses to
Summarize Text · 799529 face and body detection in the Vision framework a local model or a cloud model? ·
799484 Foundation Models framework dyld symbol errors after macOS 26 Beta 2 - LanguageModelSession constructor
missing · 789182 LanguageModelSession always returns very lengthy responses

Page 8 exists but was not enumerated. **[UNVERIFIED — page 8 contents]**

### 2.8 Evaluations topic — COMPLETE (only 3 threads exist)

| Thread ID | Title | Author | Replies | Views |
|---|---|---|---|---|
| 833822 | Vision evaluations | sfrunner | 0 | 289 |
| 833729 | Evaluations for non-Swift languages | ardysingh | 1 (Apple, accepted) | 291 |
| 832053 | Performance and customization of alternate options | progressneverstops | 1 (Apple, recommended) | 369 |

**Signal: the Evaluations forum is essentially empty.** Three threads, all from WWDC26 week (Jun 10–11 2026), one
unanswered. This is a *huge* documentation gap opportunity — nobody has written anything about Evaluations except Apple.

### 2.9 Apple Intelligence topic — page 1 (= RSS capture)

835554 Siri AI broken ("Uh oh, something went wrong.") · 838984 iPhone 16 Pro failing to install new Siri Beta ·
838996 / 838997 Siri Ai iPhone 12 (duplicate posts) · 838857 Suggestion for the SiriAI in European Union ·
838735 Apple inteligente (noise) · 837184 Pls give me new siri (noise) · **838329 Is `.appEntityIdentifier` +
`Transferable` the intended way to let Siri send an on-screen image to another app? (iOS 27)** ·
835482 qwen3.5 free offline plugin for xcode · 835603 Apple Intelligence (waitlist) · 838031 Machine learning (noise) ·
837555 New Apple Intelligence - Writing tools removal · 837566 Writing tools · 837612 Having to zoom out for Siri to
extract information · **837249 Siri AI's onscreen awareness can't understand an AppEntity without a schema?** ·
836435 Can output images from `imagePlaygroundSheet` be used as input for third-party video generation APIs? ·
836451 I got old Siri UI instead · **836316 iOS 27 `ImagePlaygroundViewController.Delegate` not working?** ·
836194 Where is my new siri?? · 836118 Joined waitlist for Siri AI

### 2.10 Apple Intelligence topic — page 2

835835 Siri AI Waitlist 100+ Hours · 832553 Indexing and Siri wait list · **835903 Siri AI shows raw
`TypedValueToContentGraphResolutionErrorDomain` error 4 to user** · 832636 iOS 27 Beta 1: iPhone 17 reverted to Old
Siri instead of New Siri · 832544 S5 - Specific Siri Security Situation in Slovakia · 830104 Wait Time for Siri AI
waitlist · 832517 New siri AI wait list · 834640 iPadOS 27 beta: Missing Apple Intelligence waitlist (UPDATED) ·
831301 Experience with Siri AI · **829586 Confused about App Intents integration in iOS27** (14 replies, 1k views —
the most-discussed AI thread found) · 834557 Siri AI waitlist · 835141 Critical: iOS 27 beta Settings crashes on
Wi-Fi Calling / E911 address page · 834660 Testing Siri on iPad if we dont have extra iPhone? · 834701 I need Siri ai ·
834966 Stuck on Siri / Apple Intelligence Waitlist for 100+ Hours on macOS 27 Beta (M4 Mac) · 834650 Is it my problem
that the new siri waitlist is taking almost a week? · 835144 New (Beta) Siri-Ai · 835157 Siri ai wait time ·
835167 New Siri · 835287 No Siri AI in visionOS 27 with a non-US Apple ID

**Observation:** ~70% of the Apple Intelligence topic is end-user waitlist complaints, not developer content. The
developer-relevant threads are the App Intents / App Schema / on-screen-content ones (829586, 837249, 838329, 835903).

### 2.11 General topic — page 1 (= RSS capture)

837386 Questions for Apple Support / Apple Vision Team (Khmer OCR misrecognized as Thai, iOS 17→27 Beta 3) ·
820379 AI framework usage without user session (CoreML/Vision in a system extension XPC with no user session;
"daemon-safe frameworks list has not been updated in a while") · 837613 [iOS 27 DB3] Apple Intelligence and Spotlight
Stuck at 85-90% (`spotlightknowledged` and `biomed` loop on "Resolved entitled set identifiers to enumerate data
resources") · 836897 RDMA issue in using the thunderbolt port next to ethernet on M3 ultra mac studio ·
833200 Autocorrection and predictive text support for additional Cyrillic languages · 775988 Group AppIntents'
Searchable `DynamicOptionsProvider` in Sections · 829571 Voice to Text (rant) · 808414 Inquiry Regarding Siri–AI
Integration Capabilities · 829572 Why the waitlist I am a developer? · 828235 `performAll()` doesn't run
`TrackObjectRequest`s in parallel · 822882 Will the upcomming Mac Book Pro M6 Max has at least 256GB RAM ·
799951 Problem running `NLContextualEmbeddingModel` in simulator · **824753 MPS backend reports ~40 GiB 'other
allocations' on 48 GB M5 Pro under macOS 26.4.1, blocking large tensor operations (PyTorch)** ·
824843 Does the new API: `BNNSGraph` support quantization · 824639 `VNRecognizeTextRequest` `.accurate` model failing
to load · 820642 Official One-Click Local LLM Deployment for 2019 Mac Pro (7,1) Dual W6900X ·
743350 Is anyone working on jax-metal? · 822443 How Is useful AI (noise) ·
**821088 After loading my custom model - `unsupportedTokenizer` error** ·
**813757 Shortcut - "Use Model" error handling?**

---

## 3. VERBATIM APPLE-STAFF ANSWERS (the authoritative material)

These are the payload. Apple staff appear under several badges observed in this corpus:
**"DTS Engineer"** (often signed *Ziqiao Chen, Worldwide Developer Relations*, occasionally *-J*),
**"Frameworks Engineer"**, **"Engineer"**, **"Apple Designer"**, and one named account **Sla1708 / Sayan Lakhoua**.
All carry the "Apple" badge.

### 3.1 Adapters are discontinued in OS 27 — TWO independent confirmations

**Thread 829108 "Adapter Problem - compatibleAdapterNotFound", Frameworks Engineer (Apple), final reply:**

> "@alex_und3r, as we announced at WWDC26, custom adapters are unfortunately no longer supported as of OS 27. Instead,
> you can use the base machine-learning models that are available on people's devices or provide your own custom models
> using Core ML or Core AI. Background Assets remains a great way to deliver custom models to your users."

**Thread 831314 "Adapter Training Toolkit: updated version for OS 27?", Apple Designer (Apple):**

> "Sorry, we're no longer supporting adapters as of OS 27. I'll update the page."

Context from the OP of 831314 (tayarndt): *"Since each adapter is tied to a specific system model version, adapters
have to be retrained whenever the base model changes. The toolkit version page currently lists **26.0.0** as the
latest, noted as the last release for the OS 26 line."*

**Migration path Apple names: Core ML or Core AI for the model; Background Assets for delivery.**

### 3.2 Earlier (still-valid-for-26) adapter asset-pack answer — 829108, Frameworks Engineer (Apple)

> "Based on the code in the screenshots that you posted, it looks like you're missing a call to
> `AssetPackManager.ensureLocalAvailability(of:requireLatestVersion:)`. When you set an asset pack's download policy to
> "on demand", you're telling the system that it shouldn't download the asset pack automatically.
> `SystemLanguageModel.Adapter(name:)` expects that the asset pack already be downloaded before you call it. To fix the
> issue here, call `ensureLocalAvailability(of:requireLatestVersion:)` and wait for it to return successfully before
> constructing an `Adapter` instance."

### 3.3 Two on-device models: AFM 3 Core vs AFM 3 Core Advanced — thread 832910, Apple Designer (Apple), accepted answer

> "> Within the same OS & device family: Do the architecture, parameters, or capabilities of the on-device models vary
> based on hardware tiers (e.g., iPhone vs. iPhone Pro, or MacBook Air M5 vs. MacBook Pro with M5 Pro)?
>
> Yes. There is **AFM 3 Core** and **AFM 3 Core Advanced**.
>
> Previously, the same on-device model was available across all devices, with different model versions mentioned in the
> docs for `SystemLanguageModel`.
>
> Starting in the fall with Siri AI release:
>
> Devices with AFM 3 Core Advanced (most powerful):
> - iPhone Air
> - iPhone 17 Pro
> - iPhone 17 Pro Max
> - iPad (M4) or later with at least 12GB of unified memory
> - Mac (M3) or later with at least 12GB of unified memory
> - Apple Vision Pro (M5)
>
> All other devices: AFM 3 Core
>
> Plan to have different models. Model details and guidance will evolve over the summer's beta period."

**This is a hard capability fork developers must design for.** Note the **12 GB unified memory** floor on iPad/Mac.

### 3.4 AFM is Core AI — thread 833657, Frameworks Engineer (Apple), accepted answer

OP (kryvoff): *"Are the on-device Apple foundation models like AFM 3 Core shipped as CoreAI models or do they use some
different technology? Is it possible to open them in the Core AI Debugger to understand them in detail?"*

> "All on-device Apple Foundation Models are powered by Core AI."

(The Core AI Debugger sub-question was **not** answered.)

### 3.5 Context window, schemas, images, versioning, concurrency — thread 833642, Frameworks Engineer (Apple)

The single densest Apple answer in the corpus. OP (gromgrom) asked six questions; Apple answered:

- **Context window:** 4K (4096) token context window. **Overflow handling is developer-managed, not automatic.**
- **Token profiling:** the `usage` property on `LanguageModelSession.Response`, plus Instruments.
- **Mitigations named:** Dynamic Instructions, the Foundation Models Utilities package, delegating sub-tasks to new
  sessions.
- **Guided generation:** supports any JSON-representable schema; **no published hard limits** on nesting depth, enum
  count, arrays, optionals; smaller/simpler schemas perform better; failure mode is *an error*, not silent
  malformation; **tool arguments always follow the defined schema.**
- **Image input:** **no set resolution restriction** (framework may resize); **unlimited image count per prompt**,
  bounded only by the context window; broad format support; **image input does not change which model services the
  request** — an on-device call stays on-device.
- **Model versioning:** **no pinning API and no version-retrieval API.** Recommended mitigation: use the
  **Evaluations framework** to catch regressions between OS updates.
- **Concurrency:** the OS limits concurrent requests; background throttling is possible on iOS; design for delays and
  cancellations in background tasks.

A community reply in the same thread (divyaravi11992, self-described Senior iOS Engineer — **NOT Apple**) adds:
*"PCC has 32K context window vs. 4K on-device."* **Treat the 32K number as community-sourced, not Apple-confirmed.**

### 3.6 4K token limit (original, iOS 26 era) — thread 790736, DTS Engineer (Apple), signed "-J"

> "You are correct that currently the token limit for Foundation Models framework is around 4,000. There is no guarantee
> that this will stay the same forever or across devices, however, so we encourage developers to write their code in a
> way that is ready to handle the context window limit when it arises.
>
> As mentioned in this session, your app can catch the `exceededContextWindowSize` error and handle accordingly. One
> suggestion for this is to summarize a session's transcript thus far, and create a new session with the condensed
> transcript, but the exact implementation will depend on your use-case."

### 3.7 `tokenCount(for:)` shipped in 26.4 — thread 817502, DTS Engineer (Ziqiao Chen)

> "A good news is that, since iOS 26.4 (and friends), we have the following API that returns the token count for the
> specified instructions:
>
> - `tokenCount(for:)`
>
> You might give it a try and let us know if that helps your use case."

OP's complaint (ilkomiliev) that the guide should address: *once `exceededContextWindowSizeError` is caught, all
context is lost, and the context window size is not exposed by the API.* Referenced doc:
**TN3193: Managing the on-device foundation model's context window**
`https://developer.apple.com/documentation/technotes/tn3193-managing-the-on-device-foundation-model-s-context-window`

### 3.8 iOS 27 session/transcript changes + DynamicProfiles — thread 835927, Frameworks Engineer (Apple)

> "The way you're doing compaction is generally correct, and recreating the session with the new transcript is correct
> if you're targeting **iOS 26**.
>
> In **iOS 27**, session's `transcript` property is now **mutable**, and transcript has a **`history` accessor** for
> updating everything except the instructions, so you can just use that instead of recreating the session.
>
> We've also introduced the notion of **`DynamicProfiles`** as a way to clip into the session lifecycle without having
> to wrap it, and open sourced some context management utilities similar to your own! You can use them as-is, or use
> them as inspiration to create your own context management modifiers to vend to others."

Linked: `https://github.com/apple/foundation-models-utilities/tree/main/Sources/FoundationModelsUtilities/History`

### 3.9 `summarizeHistory` internals + `DynamicProfileModifier` — thread 833706

**Frameworks Engineer (Apple):**

> "The `summarizeHistory` modifier allows customization of the `instructions` which are used to produce the conversation
> summary. However, it will condense all entries into a `.prompt` entry.
>
> If you're looking to preserve `.toolCalls` entries during summarization, you should be able to implement your own
> modifier using **`DynamicProfileModifier`** and either **`historyTransform`** or lifecycle modifiers (like
> **`onPrompt`**) to define your own summarize operation. The agentic app experiences session talks through these
> concepts: https://developer.apple.com/videos/play/wwdc2026/242/"

**Apple Designer (Apple), same thread:**

> "Hi! 'Summarize History' modifier currently doesn't support preserving metadata like tool call IDs.
>
> However, the 'Summarize History' modifier is implemented by combining a few primitives in Foundation Models — it asks
> a language model to summarize `transcript` when there's a prompt event (`onPrompt`), and overwrite the session history
> using summarization results.
>
> You can also create your own modifier to preserve metadata while summarizing events."

Source file named: `https://github.com/apple/foundation-models-utilities/blob/main/Sources/FoundationModelsUtilities/History/SummarizeHistory.swift`

### 3.10 Dynamic Profile switching + context reconciliation — thread 833626, Frameworks Engineer (Apple), accepted

OP: *"When using Dynamic Profiles to switch between the on-device model and Private Cloud Compute mid-session, how is
the context window reconciled…?"*

> "By default, the same transcript is shared between each Profile. So if you move from a Profile using
> `PrivateCloudComputeLanguageModel` to one using `SystemLanguageModel` and the transcript is over
> `SystemLanguageModel`'s context size limit, you'll hit a context limit exceeded error.
>
> The recommended approach here is to apply the **`historyTransform`** modifier to your `SystemLanguageModel` Profile.
> There are also some other common strategies like using the **"phone-a-friend" pattern** or **session properties** as
> well. You can learn more in the agentic app experiences session:
> https://developer.apple.com/videos/play/wwdc2026/242"

### 3.11 Tool-call interception — thread 833610, Apple Designer (Apple), marked the official answer

Apple introduced:
- the **`DynamicProfile`** API with lifecycle event listeners including **`onToolCall`**
- Recommended WWDC26 sessions: *"Secure your app: mitigate risks to agentic features"* (approval/rejection) and
  *"Build agentic app experiences with the Foundation Models framework"* (dynamic tool modification)

**Developer-reported limitation (fbeeper, follow-up):** `onToolCall` **propagates errors and stops the entire turn's
loop**, preventing fine-grained rejection of an individual tool call without ending the conversation. Wrapping the
`Tool` conformance is still needed for non-fatal feedback. Filed **FB23092325**.

### 3.12 Strict RAG / forcing tool use — thread 833692, Frameworks Engineer (Apple), Recommended

> "You can use `.toolCallingMode` with `DynamicProfiles` for this."

Linked API:
`https://developer.apple.com/documentation/foundationmodels/languagemodelsession/dynamicprofile/toolcallingmode(_:)`

### 3.13 Multi-modal / custom return types — thread 833683, Frameworks Engineer (Apple)

> "Yes, absolutely! You can use a **`CustomSegment`** to provide anything back that may not be fully defined in the
> framework currently.
>
> Additionally, their [sic] is a **SKILL.md** file in the Foundation Models Utilities that can help build a
> `LanguageModel` implementation."

### 3.14 Error pattern-matching across the three error types — thread 831404, Frameworks Engineer (Apple)

Verbatim code from the Apple reply:

```swift
let session = LanguageModelSession()
let stream = session.streamResponse(to: "Tell me about origami.")

do {
    for try await partialResponse in stream {

    }
} catch let error as LanguageModelError {
   
} catch let error as LanguageModelSession.Error {

} catch let error as LanguageModelSession.GenerationError {
   // Deprecated in 27.0
} catch {
    
}
```

**Three distinct error types exist**: `LanguageModelError`, `LanguageModelSession.Error`,
`LanguageModelSession.GenerationError` (**deprecated in 27.0**).

### 3.15 THE SIMULATOR TRAP — thread 831404, Apple Designer (Apple), accepted answer

The most important debugging fact in this entire corpus:

> "So currently we are _not_ able to replicate this issue on macOS 27.0 and Xcode 27.0, but given similar historical
> issues we had at launch last year, I highly suspect the underlying cause is that you're running macOS 26.
>
> **Why?** Xcode 27.0 contains the latest SDK, but the on-device `SystemLanguageModel` is actually built into the OS.
> **Meaning** that when you run simulator from Xcode, the simulator is actually **"punching out" to macOS** to run the
> model, using the 26.5 model inference code in the OS. Whenever we see "weird" errors like this, it's usually an
> underlying incompatibility between the Xcode SDK and OS for running the model. :(
>
> **Suggested Fix** Update a physical device to 27.0."

Corroborating DTS reply in thread 837226: *"Apple Intelligence and the `FoundationModels` framework rely heavily on
on-device hardware"* — test on a physical device, specifically iOS 27.0 beta 3 (**24A5380h**, released July 6).

### 3.16 PCC does not work in Simulator — thread 831998, Frameworks Engineer (Apple), accepted answer

> "Hi! There is a known issue that Private Cloud Compute does not currently work in simulators.
>
> https://developer.apple.com/documentation/ios-ipados-release-notes/ios-ipados-27-release-notes#Foundation-Models
>
> > Private Cloud Compute might not work when you use simulators. (**177684296**)
> >
> > **Workaround: Use a physical device running OS 27.0.**"

The failing error, verbatim from the OP (Thomvis):

```
Error Domain=FoundationModels.LanguageModelError Code=-1 "The operation couldn't be completed. (FoundationModels.LanguageModelError error -1.)" UserInfo={NSMultipleUnderlyingErrorsKey=(
         "Error Domain=FoundationModels.LanguageModelError Code=-1 \"(null)\" UserInfo={NSMultipleUnderlyingErrorsKey=(\n    \"Error Domain=ModelManagerServices.ModelManagerError Code=1046 \\\"(null)\\\" UserInfo={NSMultipleUnderlyingErrorsKey=(\\n)}\"\n)}"
     ), NSLocalizedDescription=The operation couldn't be completed. (FoundationModels.LanguageModelError error -1.)}
```

**Undocumented error code: `ModelManagerServices.ModelManagerError Code=1046`.** OP: *"Maybe error code `1046` means
something, but I can't find a mention of it in the docs."* Never explained by Apple. A second developer (isXander)
reports the same `-1` on a **physical iPhone 17 Pro Max with New Siri enabled**, so `-1` is not simulator-exclusive.

Also from this thread: **removing the Private Cloud Compute entitlement triggers a `fatalError`** at runtime, and
`model.isAvailable` returns `true` even when the call fails.

### 3.17 PCC eligibility — thread 835897, DTS Engineer (Ziqiao Chen)

- On-device Foundation Models (`SystemLanguageModel`) have **no limits** for any developer.
- **PCC access** has eligibility criteria at `https://developer.apple.com/private-cloud-compute/`.
- Apps with **more than 2 million first-time app downloads** across a long time span are **ineligible for PCC**.

**Verbatim from `https://developer.apple.com/private-cloud-compute/` (fetched this session):**

> Access to PCC is available to developers who meet the following criteria:
> - Are enrolled in the App Store Small Business Program.
> - Have fewer than 2 million first-time app downloads from any of their apps on the App Store.
> - Have the Private Cloud Compute entitlement assigned to their account.

> Where Apple Intelligence is available, eligible developers can use PCC in their apps distributed on the App Store,
> and test PCC features via TestFlight or ad hoc distribution. **Installs during testing are not counted as first-time
> app downloads.**

> If any app subsequently exceeds the 2 million first-time downloads threshold, or the developer is no longer enrolled
> in the App Store Small Business Program, the developer will be notified and must **migrate to an alternative solution
> within 6 months**.

Cost: **no cloud API cost for eligible developers.** Entitlement request link: `/contact/request/private-cloud-compute/`.

Thread 833641 (Frameworks Engineer, Recommended) restates: *"If your app exceeds the 2 million first-time downloads
threshold, you will be notified and must migrate to an alternative solution within 6 months."*

### 3.18 PCC entitlement mechanics — thread 834749, Apple Designer (Apple), accepted

> "The entitlement application is what you need to 'apply' for the program, and this entitlement in Xcode is what allows
> your app to access PCC."

Thread 829539, **Sla1708 / Sayan Lakhoua (Apple)**, accepted:

> "You can now request access to the Private Cloud Compute (PCC) Entitlement directly: Request Private Cloud Compute
> (PCC) Entitlement — https://developer.apple.com/private-cloud-compute/
>
> Please note that you must meet certain eligibility requirements to develop with Private Cloud Compute.
>
> To learn more about adding server-side intelligence to your apps, check out the documentation: Adding server-side
> intelligence with Private Cloud Compute —
> https://developer.apple.com/documentation/FoundationModels/adding-server-side-intelligence-with-private-cloud-compute"

Gotcha reported by rickystone in the same thread: the PCC request page **500'd** during WWDC26 week; the entitlement
can also be requested from the bottom of the "Adding server-side intelligence…" doc page.

### 3.19 No Required Device Capability for Apple Intelligence — thread 836810

**Frameworks Engineer (Apple):**

> "The recommendation on the App Store side is to provide some baseline functionality to all users, regardless of
> whether Apple Intelligence is available. **The App Store doesn't support a required device capability for Apple
> Intelligence.** Even on compatible devices, there are a number of reasons why Apple Intelligence could be unavailable,
> such as if the user selected an unsupported Siri language, is located in an unsupported region, or opted out of Apple
> Intelligence."

**Apple Designer (Apple), same thread — key architectural framing of what "Foundation Models" now means:**

> "As of WWDC 2026, Foundation Models framework covers both on-device foundation models and server-based models…
> _and_ both Apple Foundation Models as well as any other LLMs. So 'foundation models' can mean a bunch of different
> things and a bunch of possible models, which is part of the reason why there isn't currently a clean device-capability
> flag.
>
> The full list of Apple Intelligence requirements (for Apple Foundation Models) can be found here
> https://support.apple.com/en-us/121115 and include a combination of regional and hardware requirements.
>
> Models from other sources can be used with Foundation Models using **MLX or CoreAI**, so you can still reach users
> with hardware that can't run Apple's on-device foundation model.
>
> **So... what can you do?**
>
> 1. Run an availability check as soon as you launch your app. For example
> https://developer.apple.com/documentation/foundationmodels/systemlanguagemodel/isavailable for the on-device model.
> Availability can tell you additional information about compatibility... like if the model is downloading or not
> available for that language. From a UX standpoint, **try to check availability before anyone agrees to pay for your
> app's service**, to avoid someone paying for what they can't use.
>
> 2. Figure out if you can use a different model as backup, if Apple's on-device foundation model isn't compatible with
> the device. Any server or local LLM might do."

### 3.20 FM in app extensions & memory — thread 833575, DTS Engineer (Ziqiao Chen), Recommended

> "The system language model (`SystemLanguageModel`) is **not loaded into the app / extension's memory**, and so using
> it **doesn't count on the memory limit of your extension**. If you are using your own on-device model, the model will
> be loaded to the memory of your app / extension, and so you will need to test if that is fine for your extension.
> **Note that some extensions don't allow XPC due to privacy reason, and hence can't use a model via the Foundation
> Models framework.**"

The OP's follow-up — *"Does this include `SystemLanguageModel`?"* — is **unanswered**. Original question was about
`MessageFilterExtension`. See also feature-request thread 810398 "Allow Foundation Models in MessageFilter Extensions".

### 3.21 Background / NPU priority — thread 833666, Frameworks Engineer (Apple), Recommended

OP: *"While we now know about the `continued-processing.gpu` entitlement for background tasks, is there a similar
NPU-specific entitlement or priority flag to ensure that an on-device foundation model isn't preempted by system-level
Apple Intelligence features while the app is in the background?"*

> "The OS manages the requests for the on-device LLM automatically, based on the system conditions (like thermals).
> **There's no entitlement or API to influence this.**"

### 3.22 Non-App-Store / notarized macOS apps — thread 832033, Frameworks Engineer (Apple)

> "Yes, non-App Store apps can use the Foundation Models framework to access the on-device system model."

(No entitlement named. **[UNVERIFIED]** whether PCC works for non-App-Store distribution — PCC page says "distributed
on the App Store … test via TestFlight or ad hoc".)

### 3.23 macOS/Europe availability — thread 836760, Frameworks Engineer (Apple)

> "The Foundation Models framework **should be available in Europe even if Siri AI is not enabled**. Please file a bug
> report via Feedback Assistant and be sure to include a sysdiagnose to help us investigate."

**Contradicted in practice** by thread 835211 (unanswered): on iOS 27 Beta 1, `SystemLanguageModel.default.availability`
returns `.appleIntelligenceNotEnabled` unless the user has enabled "Siri"/"Hey Siri" or "Press Side Button for Siri".
**This coupling is a live, unresolved gate.**

### 3.24 Language / locale gating — thread 797271, Frameworks Engineer (Apple)

> "Foundation Models support the same set of languages as Apple Intelligence. You can find the list of currently
> supported languages here." → `https://support.apple.com/en-us/121115`

Thread 805378 (alarno) reply from MB-Researcher — badge status ambiguous in the fetch, treat as
**semi-authoritative / [UNVERIFIED as Apple staff]**:

- Apple Intelligence is based on **Siri language settings, NOT system language**. Path:
  **Settings > Apple Intelligence & Siri > Language**.
- 8 languages added in that cycle: **Danish, Dutch, Norwegian, Portuguese (Portugal), Swedish, Turkish, Chinese
  (Traditional), Vietnamese**.
- Framework API named: **`supportsLocale(_:)`** (rendered lowercase `supportslocale(_:)` in the fetch) — it *"checks
  against user's language settings… Returns `true` if a *close* language can be supported. Example: If user app is set
  to Catalan, `supportsLocale(_:)` returns true since Spanish (closely related) is supported."*
- Doc: "Support languages and locales with Foundation Models"
  `https://developer.apple.com/documentation/foundationmodels/support-languages-and-locales-with-foundation-models`

The OP's requested-but-not-shipped API: `LanguageModelSession(preferredLanguage: "es-ES")`.

### 3.25 watchOS — thread 835987, Frameworks Engineer (Apple), accepted

Build error on watchOS 27 Beta 2:

```
/Applications/Xcode-beta.app/Contents/Developer/Platforms/WatchOS.platform/Developer/SDKs/WatchOS27.0.sdk/System/Library/Frameworks/FoundationModels.framework/Modules/FoundationModels.swiftmodule/arm64e-apple-watchos.swiftinterface:6:15 Unable to resolve module dependency: 'CoreImage'
```

> "This is a known bug."

### 3.26 watchOS PCC pairing requirement — thread 834652 (OP self-answer, no Apple reply)

> "No, not only does the Watch have to be running WatchOS 27, it also needs to be paired to an iPhone with Apple
> Intelligence enabled. This is despite the fact that PCC queries from WatchOS 27 go straight to the server and don't
> require the paired iPhone at all 🤷‍♂️"

**[UNVERIFIED by Apple]** but a high-signal deployment gotcha: Apple Watch Series 11 + iPhone 15 = no PCC.

### 3.27 `MLXFoundationModels` module location — thread 836264, Engineer/DTS (Apple), accepted

> "This is being introduced to `mlx-swift-lm` in **PR#334** (see here: https://github.com/ml-explore/mlx-swift-lm/pull/334)."

Relates to WWDC26 session 339 *"Bring an LLM provider to the Foundation Models framework"*
(`https://developer.apple.com/videos/play/wwdc2026/339/`), where `import MLXFoundationModels` appears in slides.

Thread 831197, Apple Designer (Apple): *"I would suggest heading over to https://github.com/ml-explore/mlx-swift-lm to
see if that package has what you're looking for."*

### 3.28 Evaluations is Swift-only — thread 833729, Frameworks Engineer (Apple), accepted

> "Evaluations is a Swift-based framework. So you would need to call the Swift APIs from the other language. For that,
> you can look at our documentation on language interoperability"

### 3.29 `ModelJudgeEvaluator` — thread 832053, Engineer (Apple), Recommended

> "The `ModelJudgeEvalutor` [sic, Apple's typo] is used to evaluate a response where the score is subjective - e.g.
> 'is this a good explanation'.
>
> There are some good examples here:
> https://developer.apple.com/documentation/evaluations/scoring-with-model-as-judge-evaluators
>
> And in the sample code project:
> https://developer.apple.com/documentation/evaluations/book-tracker-using-evaluations-to-evaluate-an-intelligent-feature
>
> You can use it to evaluate responses from the `PrivateCloudComputeLanguageModel`. You just need to set up your
> `LanguageModelSession` correctly:"

```swift
let session = LanguageModelSession(model: PrivateCloudComputeLanguageModel())
let response = try await session.respond(to: "Analyze this document...")
```

Doc URL for the type: `https://developer.apple.com/documentation/evaluations/modeljudgeevaluator`
The MLX-vs-AFM performance half of the question was **not answered**.

### 3.30 Hallucinating numbers — thread 833560, Frameworks Engineer (Apple), Recommended

> "I would look at the Guided Generation talk in 'Meet Foundation Models' from last year.
>
> Additionally, adding tools that can do calculations for the model (i.e. average, sum, etc) instead of the model trying
> to do them can help as well."

### 3.31 CoreSpotlight custom attributes are reachable — thread 833658, Engineer (Apple), accepted

> "`IndexedEntity` is backed by a `CSSearchableItem` that can be extended with any additional metadata on the item,
> whether system attributes or custom attributes, and are available for in-app search with any of CoreSpotlight's query
> APIs, including `SpotlightSearchTool`.
>
> For reasoning over custom attributes, you can describe them in the instructions for your language model session, or
> use **dynamic guidance in SpotlightSearchTool's configuration**."

Doc surfaced by OP: `https://developer.apple.com/documentation/appintents/making-app-entities-available-in-spotlight`

### 3.32 SpotlightSearchTool schema bug is a KNOWN ISSUE — threads 832534 / 833651

**Thread 833651, DTS Engineer (Apple):** *"Thanks for your question. This is a known issue discussed here."* (→ 832534)

Verbatim OP description (bkusserow, 833651) — the mechanics:

> "The root cause is a mismatch between two things the framework sends to the model in the same tool definition:
> - the human-readable `description` ('Call format'), which presents the top-level arguments as
>   `{ root, modelComposition, … }`, and
> - the `parameters` JSON Schema (`FullArguments`), which requires
>   `{ "query": { "type": "search", "value": { root, modelComposition, … } } }`.
>
> A model that follows the description is guaranteed to fail the schema."

Failure surface: `LanguageModelSession.ToolCallError` with underlying **"Failed to parse generated content."**
Manual wrapping of the args makes it parse and search correctly. `Query` is a **`QueryType` union** and a search must
be wrapped in **`DiscriminatedSearch`**.

Secondary bug in the same post: **`CoreSpotlightSource.fetchAttributes` has no effect** on returned attributes on the
agentic-search path. `kMDItemDescription` only comes back when the in-query `SearchArguments.fetchAttributes` lists it.
`searchableIndexDelegate` **was never invoked in any configuration tried (including `.dynamic`)**.

### 3.33 Other SpotlightSearchTool failures

**Thread 837226 (Hunter)** — console error, verbatim:

```
InferenceError::hostFailed::InferenceError::inferenceFailed::TokenGenerationCore.GuidedGenerationError.invalidConfiguration(errorMessage: "Tool Choice requires tools") in response to ExecuteRequest
Error during session.respond. description="The operation couldn't be completed. (FoundationModels.LanguageModelError error -1.)"
Returning empty Spotlight result. elapsedMs=3254 toolReplies=0 totalSearchItems=0 uniqueSearchItems=0
```

Triggering code:

```swift
let session = LanguageModelSession(tools: [tool]) {
    spotlightSearchInstructions
}
let response = try await session.respond(to: prompt, options: GenerationOptions(toolCallingMode: .required))
```

Reproduced on **iPhone 17 Pro Max, iOS 27 beta 3**. Filed **FB23643759**. Still open. Note the error text —
**"Tool Choice requires tools"** — fires even though tools *were* passed, i.e. the tool array isn't reaching the
inference layer. Note also `GenerationOptions(toolCallingMode:)` here vs. the `DynamicProfile.toolCallingMode(_:)`
modifier recommended in 833692 — **two surfaces for the same concept**.

**Thread 838904 (BlueFox123)** — Apple Designer (Apple) reply, verbatim:

> "Whelp, that's totally a bug. 🐛
>
> You're doing everything correctly! That's not an error you should ever see normally.
>
> Thanks for reporting! I'm filing a bug report for this, although it would definitely help if you can tell me:
> - Did you update your Mac right before this error or within the past few hours before the error?
>
> Rebooting your Mac _should_ resolve the issue…"

The error, verbatim:

```
Model Catalog error: Error Domain=com.apple.UnifiedAssetFramework Code=5000 "There are no underlying assets (neither atomic instance nor asset roots) for consistency token for asset set com.apple.modelcatalog" UserInfo={NSLocalizedFailureReason=There are no underlying assets (neither atomic instance ...
```

Repro code:

```swift
import CoreSpotlight
import FoundationModels
  
let tool = SpotlightSearchTool()

let session = LanguageModelSession(tools: [tool])

let response = try await session.respond(to: "What hikes have I gone on?")
```

OP reports **rebooting did NOT fix it** and it persisted across beta 3 → beta 4. Environment string used:
**"macOS Golden Gate Developer Beta 4"** — *Golden Gate appears to be the macOS 27 codename* (also used by Thomvis in
831998: "macOS Golden Gate on a MacBook Pro M1").

### 3.34 `.anyOf` is broken — thread 812501 (Apple staff reproduced it)

Apple Designer (Apple) **confirmed the bug on Apple's end** after reproducing with:

```swift
@Generable
struct Arguments {
    @Guide(description: "The city to get information about.", .anyOf(["London", "New York", "Paris"]))
    let city: String
}

func call(arguments: Arguments) throws -> String {
    print("Arguments are", arguments.generatedContent)
    let cityName = arguments.city
    let cityInfo = getCityInfo(for: cityName)
    return cityInfo
}
```

Model generated **"Beijing"** despite the constraint. Frameworks Engineer noted it **reproduces on iOS 26.2**.

Apple's answer to "what does `.anyOf` actually do?": **both** — (1) list all options in the schema presented to the
model AND (2) constrain generation at prediction time. It just doesn't work.

Apple-recommended workarounds:
1. Validate inside the tool and return a corrective string, e.g.
   `default: return "Not a valid city. City must be one of:\(validCities)"` — *but the OP reported the model then gets
   stuck in loops re-calling with invalid args.*
2. Drop `.anyOf` and put the constraint in ALL-CAPS instructions:
   ```
   You can ONLY call the tool getCityInfo for the these cities: "London", 
   "Paris", "New York". For questions about all other cities you MUST tell 
   the user "Sorry, I can't look up that city."
   ```

Apple Designer's *initial* (wrong-in-this-case but generally true) hypothesis is itself a documented gotcha:

> "Once a `LanguageModelSession` is initialized with a tool, the `parameters` property is **computed once and never
> updated**. If the schema initially has an empty array, the `.anyOf` constraint won't be enforced even if sections are
> later added."

Full `GenerationSchema`-based tool the OP used (verbatim, thread 812501):

```swift
struct SectionReader: Tool {
    let article: Article
    let sections: [String]
    
    let name: String = "readSection"
    let description: String = "Read a specific section from the article."
    var parameters: GenerationSchema {
        GenerationSchema(
            type: GeneratedContent.self,
            properties: [
                GenerationSchema.Property(
                    name: "section",
                    description: "The article section to access.",
                    type: String.self,
                    guides: [.anyOf(sections)]
                )
            ]
        )
    }
    
    func call(arguments: GeneratedContent) async throws -> String {
        let requestedSectionName = try arguments.value(String.self, forProperty: "section")
        ...
    }
}
```

And the `DynamicGenerationSchema` variant that also failed (thread 811620):

```swift
let citiesDefinedAtRuntime = ["London", "New York", "Paris"]

let citySchema = DynamicGenerationSchema(
    name: "CityList",
    properties: [
        DynamicGenerationSchema.Property(
            name: "city",
            schema: DynamicGenerationSchema(
                name: "city",
                anyOf: citiesDefinedAtRuntime
            )
        )
    ]
)

let generationSchema = try GenerationSchema(root: citySchema, dependencies: [])
let tools = [CityInfo(parameters: generationSchema)]
```

### 3.35 Guardrails: only `.default` (2025) → `.permissiveContentTransformations` (2026)

**Thread 788053 (Jun '25), DTS Engineer (Ziqiao Chen):**

> "As of today, you only have the `.default` option, meaning that you use the system-provided guardrail. I'd suggest
> that you file a feedback report if the system guardrail doesn't work for your use case (over restrictive, for
> example)"

Blocked prompt example that started the thread: *"How can I kill deer ticks using a clothing treatment?"*
Community: *"I get safety violations just asking for a taco recipe."*

**Thread 835777 (Jun '26), Frameworks Engineer (Apple):**

> "If you are seeing guardrails false positives, we recommend filing a Feedback from the Feedback Assistant. Make sure
> to include as much information as possible about the transcript: **tools exposed, instructions, prompt**…"

OP's initializer, verbatim, plus the crucial developer-known limitation:

```swift
LanguageModelSession(model: SystemLanguageModel(guardrails: .permissiveContentTransformations))
// I'm aware that .permissiveContentTransformations does not apply to Generable, but I'd really really really really love it, if it did!.
```

**So: `SystemLanguageModel(guardrails:)` exists with at least `.default` and `.permissiveContentTransformations`, and
`.permissiveContentTransformations` DOES NOT apply to `Generable` / structured output.** That is a load-bearing
undocumented-ish fact repeated by multiple developers.

**Thread 820819 (iOS 26.4 regressions), Frameworks Engineer (Apple):**

> "Thank you for your feedback! Can you submit a **`LanguageModelFeedback`** through Feedback Assistant for this
> specific issue?" → `https://developer.apple.com/documentation/foundationmodels/languagemodelfeedback`

Concrete 26.4 regressions reported: *"Is the car plugged in?"* works; *"Tell me if the car is plugged in"* does not.
The word **"frunk"** triggers Guardrail Violation. **"Lock Pride"** (Pride = the car's name) triggers Guardrail
Violation. Tool calling *"only works half the time for really obvious things."*

**Thread 833614 (Improved Guardrails Error Handling), DTS Engineer (Apple):**
> "Thanks for filing the feedback report. It's under the investigation of Foundation Models framework team."
Use case: a digital-wellbeing app ("one sec") asking the model whether a user is in deep distress, to show crisis
support resources — **guardrails block exactly the safety-critical path.** Radar **FB20828230**.

### 3.36 iOS 27 refusal regression (NO Apple reply) — thread 836673

Health app, glucose + menstrual-cycle summaries of the user's own data. Worked on iOS 26.x since early 2026; **every
prompt refused on iOS 27 beta 2**.

- Error type is **`LanguageModelError`** ("The model refused to answer" / "May contain sensitive content"),
  **NOT `GenerationError.guardrailViolation`.**
- `SystemLanguageModel(guardrails: .permissiveContentTransformations)` does **not** help.
- "Classifier passes, but model itself refuses" — i.e. a **model-level** refusal, downstream of the guardrail
  classifier.
- Trigger terminology: **"luteal phase," "progesterone," "glucose," "time in range," "diabetes"**.
- Filed **FB23513774**. Corroborated by a second dev (journaling app) on iOS 27 beta.

**This is the most commercially dangerous unanswered thread in the corpus.** Two error surfaces for refusal
(`LanguageModelError` vs `GenerationError.guardrailViolation`) with different semantics.

### 3.37 `com.apple.SensitiveContentAnalysisML error 15` — thread 836285

Trivial prompt, total failure:

```swift
#Playground {

    let session = LanguageModelSession()
    
    let response = try await session.respond(to: "List all states of USA.")
    
    print(response.content)
    

}
```

→ `The operation couldn't be completed. (com.apple.SensitiveContentAnalysisML error 15.)`
Xcode 27 beta 2. Toggling Apple Intelligence off/on did not help. Apple replies were only "file a bug" / "was it fixed
in the latest beta?". **Error domain `com.apple.SensitiveContentAnalysisML` code 15 is undocumented.**

### 3.38 Image input + bounding boxes — thread 838613, Apple Designer (Apple), Recommended

> "Really great feedback, thanks! We'll get this to the Vision framework + FoundationModels engineers.
>
> In the meantime, the Vision framework is the modern Swift successor to VisionKit that has a bunch of saliency and
> classification APIs that may be helpful."

OP's finding — **FM can name objects but cannot reliably localize them.** Coordinate systems tried: raw pixels;
normalized 0…1; integer percent 0…100; "soft location" descriptors. "Soft location" was most consistent but
incomplete; raw pixels were "almost usable but often off by 1–2× the object width/height or cluster rectangles at top
of image." OP's suspicion: **"Foundation Models downsamples images to 896px on longest dimension."** **[UNVERIFIED —
developer inference, not Apple-confirmed. But 896 is a plausible ViT tile size and worth chasing.]**

The `Attachment` + `Prompt` builder API appears verbatim here — note `Attachment(_:orientation:)`:

```swift
let prompt = Prompt {
    "Describe this \(imageWidth)×\(imageHeight) image. Bounding box coordinates are in pixels: (0,0) is top-left, (\(imageWidth),\(imageHeight)) is bottom-right."
    Attachment(modelImage.cgImage, orientation: modelImage.orientation)
}
```

### 3.39 `ChatCompletionsLanguageModel` version-path bug — thread 838444, Apple Designer (Apple), accepted

The offending private method, verbatim from
`https://github.com/apple/foundation-models-utilities/blob/376ca60e61985369d5067bd3c575bdb6a13f0e1b/Sources/FoundationModelsUtilities/LanguageModels/ChatCompletionsLanguageModel.swift#L634`:

```swift
private func buildURLRequest(for request: ChatCompletionRequest) throws -> URLRequest {
    let isVersioned = baseURL.pathComponents.contains("v1")
    let endpoint = isVersioned ? "/chat/completions" : "/v1/chat/completions"
    let url = baseURL.appendingPathComponent(endpoint)
    ...
  }
```

Breaks any provider not on `/v1` (example: Volcengine Ark uses `/api/v3`). Resulting error:

```
HTTP error with status code 404:
{"error":{"code":"InvalidAction","message":"The specified action is invalid: /api/v3/responses/v1/chat/completions Request id: 021784381168842fdfd2e3c33d5b6eddad55ac385080e727cab08","param":"","type":"NotFound"}}
```

Proposed fix (accepted by Apple with *"Fantastic suggestion, thanks! We're on it."*):

```swift
let isVersioned = baseURL.pathComponents.contains { component in
    component.wholeMatch(of: #/v\d+/#) != nil
}
```

**Verified initializer signature from OP's working code:**
`ChatCompletionsLanguageModel(name: String, url: URL, additionalHeaders: [String: String])`, used as
`LanguageModelSession(model: model)`. Filed **FB23837262**.

### 3.40 WebKit / JS bridge — thread 833716, DTS Engineer (Ziqiao Chen)

> "The Foundation Models framework doesn't provide any JavaScript interface, but it seems that you are asking how to run
> Swift code from web content in `WKWebView`. If that is the case, WebKit provides a mechanism
> (**`WKUserContentController`**) for a web app to run your app's native code."

### 3.41 Speech generation: NO new API — threads 834149 and 832868

**Thread 834149, Apple Designer (Apple):**

> "The short answer is no. No new API has been released specific to that model. Though of course you still have the
> older existing speech synthesis APIs in AV Foundation
> https://developer.apple.com/documentation/avfoundation/speech-synthesis"

Thread 832868 (fastred) cites the WWDC26 Keynote at **30m:20s**, Craig Federighi describing the second, "even more
powerful version of our on-device model" that "lets supported products understand and generate speech." **0 replies.**

**Conclusion: the AFM 3 Core Advanced speech capability is NOT exposed to third-party developers as of July 2026.**

### 3.42 Availability is always required — thread 830161, Apple Designer (Apple)

> "The on-device foundation model _is_ part of the OS as a core part of Apple Intelligence, but a user can choose to
> turn off Apple Intelligence in Settings > Apple Intelligence.
>
> Additionally Apple Intelligence isn't available on some older phone models simply due to older hardware. Thus you'll
> need to keep checking the availability."

Unanswered follow-up: *"Does this same user opt-in apply to `PrivateCloudComputeLanguageModel`… is there a separate
availability tier for cloud-backed models?"* — **open question.**

### 3.43 Feedback workflow (Apple's own instructions) — sticky thread 791250, DTS Engineer (Apple). Thread is LOCKED.

Two methods:

**Method 1 — Xcode `#Playground` (macOS/iOS 26 Beta 4+):**
1. In Xcode, create a playground using `#Playground`.
2. Reproduce the issue by setting up a session and generating a response with your prompt.
3. In the canvas on the right, click the **thumbs-up icon** to the right of the response.
4. Follow the pop-up instructions and submit by clicking **"Share with Apple"**.

**Method 2 — Feedback report** (`https://developer.apple.com/bug-reporting/`), include:
- **Language model feedback** — "essential component containing session transcript (instructions, prompts, responses,
  etc.)"
- Retrieve it via **`logFeedbackAttachment(sentiment:issues:desiredOutput:)`**, write the data to a file, attach it.
- If system-configuration related, also capture and attach a **sysdiagnose**.

Related type: **`LanguageModelFeedback`**
(`https://developer.apple.com/documentation/foundationmodels/languagemodelfeedback`).

### 3.44 Shortcuts "Use Model" has NO error handling — thread 813757, DTS Engineer (Ziqiao Chen)

> "The answer then is that there is currently no way to detect an error from an action. I checked with the Shortcuts
> folks and they suggested that you file a feedback report with your use case to request the support of try-catch in
> Shortcuts"

Use case blocked: on-device model overflows the context window inside a Shortcut; the developer wants to retry on the
Cloud model or fall back to manual entry. **Not possible.**

### 3.45 App Intents vs App Schemas — thread 829586 (14 replies, ~1k views)

The most contested developer thread found. Community consensus after WWDC26 sessions **240, 345, 343**:

- **To expose entities/actions to new Siri and agentic features, they must conform to published App Schemas.** If your
  data doesn't fit a whitelisted domain, **there is no supported path**.
- Cited as evidence: Apple's own `TrailEntity` hiking sample maps to no published domain, so Siri cannot help users
  compare routes.
- Contradictory docs: one says *"Apple Intelligence and Siri AI work better for app intents that support a known
  schema"*; another doesn't mention custom app intents at all.
- **DTS answer for plain-text documents:** use the `.notes` schema —
  ```swift
  @AppIntent(schema: .notes.createNote)
  ```
  (references WWDC26 video 240)
- **Key distinction reported from the Apple Intelligence Group Lab:**
  1. Entity **discoverability** does NOT require conforming to whitelisted schema domains.
  2. Siri can **only take actions** that DO conform to whitelisted schema domains.
- Proposed (untested) workaround: expose custom entities via discoverability, add an in-app agent, and expose intents
  to Siri that message that agent conforming to the **Messages App Schema Domain**.
- Filed **FB23018652**. DTS characterized it as an enhancement request, not a bug.
- Meta-detail from the thread: Q&A forum posts allow **7000 characters** (not 300).

### 3.46 On-screen content handoff — thread 838329

Working pattern discovered by the community (J0hn, "Recommended"), for letting Siri send an on-screen image elsewhere:

```swift
public func collectionView(
    _ collectionView: UICollectionView,
    appEntityIdentifierForItemAt indexPath: IndexPath
) -> EntityIdentifier? {
    guard let item = dataSource?.itemIdentifier(for: indexPath) else { return nil }
    guard let fileIdentifier = try? FileEntityIdentifier.file(url: <URL>) else { return nil }
    return EntityIdentifier(for: <ENTITY>.self, identifier: fileIdentifier)
}
```

```swift
public static var transferRepresentation: some TransferRepresentation {
    FileRepresentation(
        contentType: .image,
        exporting: { entity in
            guard let url = try await entity.id.fileURL else {
                throw Errors.unableToRetrieveURL
            }
            return SentTransferredFile(url)
        },
        importing: { received in
            let attributes = try? FileManager.default.attributesOfItem(atPath: received.file.path())
            let creationDate = attributes?[.creationDate] as? Date
            let modificationDate = attributes?[.modificationDate] as? Date
            
            return <ENTITY>(
                id: try FileEntityIdentifier.file(url: received.file),
                creationDate: creationDate,
                fileModificationDate: modificationDate,
                name: received.file.lastPathComponent
            )
        })
}
```

**Rules extracted:**
- Entity must be `@AppEntity(schema: .files.file)` — a **predefined schema**, not a custom one.
- Identifier must be a **`FileEntityIdentifier`**, not a plain `String`.
- Transfer must be **`FileRepresentation` + `SentTransferredFile`**, not a generic `DataRepresentation`.
- With a custom `AppEntity` + `DataRepresentation`, "Send this to <contact>" returns *"I can't attach the image
  directly"*, and **`EntityQuery.entities(for:)` was never called** in most flows.
- "Describe this" / "Create a note" use **automatic screenshots**, not the app entity.
- **`.files.file` requires a real file on disk** — no lightweight path for transient in-memory images.
- DTS Engineer acknowledged, feedback **FB23813341**, noted similar patterns in Photos and Messages.

Related unanswered thread 837249: a hiking app's custom `AppEntity` + `EntityQuery` is executed, but *"Siri seems to
be reading the screen directly rather than retrieving data from the provided AppEntity."* Off-screen data (heart rate,
average speed from other tabs) is invisible to Siri. Same root cause: **no matching `AppSchemaEntity`.**

### 3.47 Adapter disk-space leak (26.x) — thread 823001

Even though adapters are dead in 27, this thread documents a real system path and a real Apple confirmation.

- **Symptom:** `SystemLanguageModel.Adapter(fileURL:)` leaks **~100 MB per call**. 300 calls ≈ 30 GB. One user hit
  ~239 GB, another ~104 GB (645 clones).
- **Cause:** each invocation writes `lora.part.bin` + `metadata.json` into a **new, non-content-addressed hash
  directory** under `/private/var/db/AppleIntelligencePlatform/AppModelAssets/`, written by
  **`TGOnDeviceInferenceProviderService`**. **Zero garbage collection.**
- **Invisible from userspace because SIP protects that path** — `sudo ls` / `sudo find` return "Operation not
  permitted", so `du` can't see it and it looks like APFS corruption.
- **Recovery-mode cleanup (verbatim steps from the thread):**
  1. Reboot into Recovery Mode (hold Power on Apple Silicon)
  2. Open Terminal from Utilities
  3. `diskutil apfs list` — find the Data volume (e.g. `disk3s5`)
  4. `diskutil mount disk3s5`
  5. `diskutil apfs unlockVolume disk3s5`
  6. `ls /Volumes/Data/private/var/db/AppleIntelligencePlatform/AppModelAssets/ | wc -l`
  7. `rm -rf /Volumes/Data/private/var/db/AppleIntelligencePlatform/AppModelAssets/*`
  8. Reboot
- **Apple Designer (Apple):** *"We've identified this is a current bug specific to command line tools. You will see this
  adapter memory leak from a CLI on macOS, but NOT if you load the adapter into a running Swift app."*
  — **disputed** by a second reporter who observed it from a SwiftUI app run from Xcode.
- Related feedback: **FB22523518**. Environment: macOS Tahoe 26.4.1, MacBook Air M4.

### 3.48 Adapter packaging CLI — thread 823148 (solved by OP, "Recommended")

The **only** place the FM-specific packaging command is documented in this corpus:

```
xcrun ba-package foundation-models package \
--adapter-path aurelius1.fmadapter \
--asset-pack-id fmadapter-aurelius1-9799725 \
--output-path ./aurelius1.aar \
--platforms iOS \
--on-demand
```

Findings from 823148:
1. Using the generic `xcrun ba-package package` produces a pack the **FoundationModels runtime will not recognize**.
   The correct subcommand is `xcrun ba-package foundation-models package` — *"found in adapter training toolkit source
   `produce_asset_pack.py`"*.
2. The generated manifest has `"onDemand": null`, which **Transporter rejects with ITMS-91140**.
3. **Workaround:** extract the `.aar`, change `"onDemand": null` → `"onDemand": {}` in `manifest.json`, repack, upload.
4. Then internal TestFlight delivery works and `statusUpdates` fires `.began` / `.downloading(progress)` / `.finished`.

Required Info.plist keys + entitlement from the same thread:

```xml
<key>BAHasManagedAssetPacks</key><true/>
<key>BAUsesAppleHosting</key><true/>
<key>BAAppGroupID</key><string>group.com.fiuto.shared</string>
```
Entitlement: **`com.apple.developer.foundation-model-adapter`** (on the app AND the asset downloader extension).
Extension type: **`StoreDownloaderExtension`**. Adapter ID format: `fmadapter-<Name>-<7digits>`.

API surface used:
```swift
let adapter = try SystemLanguageModel.Adapter(name: "FiutoAdapter")

let ids = SystemLanguageModel.Adapter.compatibleAdapterIdentifiers(name: "FiutoAdapter")
// ids == ["fmadapter-FiutoAdapter-1234567"]

for await status in AssetPackManager.shared.statusUpdates(forAssetPackWithID: ids.first!) {
}
```

### 3.49 Miscellaneous Apple answers

- **Thread 833650 (structured intents vs free-form), DTS Engineer:** *"This QA session focuses on the Foundation Models
  framework. Your question is related to App Intents and Siri, and so we suggest that you ask in the main forums."*
  (Pattern: the WWDC26 FM Q&A repeatedly deflected App-Intents questions.)
- **Thread 833627 (unified API for third-party cloud providers), Frameworks Engineer:** *"I believe all of your question
  about the `LanguageModel` protocol can be answered in this WWDC26 session -
  https://developer.apple.com/videos/play/wwdc2026/339"* — five substantive sub-questions (privacy boundary of
  third-party routing, capability normalization, whether custom providers become Siri-selectable, API stability before
  open-sourcing) **all deferred to a video.**
- **Thread 835165 (SkillActivation build failure), Frameworks Engineer:** *"Can you share some of the specific
  compilation errors you're seeing?"* — never resolved. **`SkillActivation` is a module in
  `github.com/apple/foundation-models-utilities`.**
- **Thread 803442 (off-device computation?)** — answered by a **community** member (MB-Researcher, badge unclear):
  *"Foundation Models only uses the on-device ~3 billion parameter foundation model. That's 100% on-device."*
  **This is now OUTDATED for 2026** — `PrivateCloudComputeLanguageModel` and third-party `LanguageModel` conformances
  exist. Keep the ~3B parameter figure as an **iOS 26-era** number.

---

## 4. Pain-point clusters — what the guides MUST cover

Ranked by thread volume × severity × how badly documented it is.

### Cluster A — "Is the model even available?" (availability & gating)
Threads: 835211, 836760, 836810, 830161, 834652, 797271, 805378, 787468, 802119, 803258, 821067, 835287.
- Availability depends on: hardware tier, **Siri/Apple Intelligence language** (not system language), region,
  user opt-out, model download state, **and (on iOS 27 b1) whether "Hey Siri"/"Press Side Button" is enabled**.
- `SystemLanguageModel.default.availability`, `.isAvailable`, `.isSupported`, `supportsLocale(_:)`,
  `.appleIntelligenceNotEnabled` — devs don't know which to use when.
- **No Required Device Capability exists.** App Store filtering is impossible; Apple mandates a baseline non-AI
  experience. Devs are angry about this (thread 836810).
- watchOS PCC requires a paired iPhone with AI enabled.
- **Guide need:** a single decision-tree/table: which API answers which question, what each failure mode looks like to
  the user, and what UX Apple actually expects (check availability before payment).

### Cluster B — Guardrails, refusals, and false positives
Threads: 788053, 787736, 797724, 797955, 802921, 817495, 820798, 820819, 821602, 833614, 835777, 836285, 836673.
This is the **single largest and longest-running** cluster; it spans Jun '25 → Jul '26 with no resolution.
- Two *different* refusal surfaces: `GenerationError.guardrailViolation` vs `LanguageModelError` ("The model refused to
  answer" / "May contain sensitive content"). The second is a **model-level** refusal that guardrail settings can't
  touch.
- `.permissiveContentTransformations` **does not apply to `Generable`/structured output.**
- Real blocked words documented: "kill", "frunk", "Pride", "luteal phase", "progesterone", "glucose", "time in range",
  "diabetes", "taco recipe", theological texts, camping/survival/fishing content.
- Apple's only remedy is "file a `LanguageModelFeedback`".
- **Guide need:** an errors-and-refusals chapter: full taxonomy, which knob affects which, retry/fallback strategies,
  prompt rewording tactics, and the `logFeedbackAttachment(sentiment:issues:desiredOutput:)` workflow.

### Cluster C — Context window management
Threads: 790736, 800238, 801504, 806542, 806779, 813757, 817502, 823423, 833642, 833706, 833712, 835927.
- 4096 tokens on-device. Not exposed as a constant. No auto-truncation.
- `tokenCount(for:)` since 26.4; `Response.usage`; Instruments.
- iOS 26 pattern (recreate session from compacted `Transcript`) vs **iOS 27 pattern (mutable `session.transcript`,
  `transcript.history`, `DynamicProfileModifier` + `historyTransform` / `summarizeHistory`)**.
- `summarizeHistory` **destroys `.toolCalls` entries** (condenses everything into a `.prompt` entry).
- Cross-profile switching (PCC 32K → on-device 4K) throws unless you apply `historyTransform`.
- Shortcuts "Use Model" can't catch the overflow error at all.
- **Guide need:** a full context-management chapter with both the 26 and 27 idioms, plus TN3193 reconciliation.

### Cluster D — Tools & guided generation don't behave as documented
Threads: 805970, 808765, 811381, 811620, 812501, 831448, 832534, 833610, 833651, 833692, 837226, 838904.
- **`.anyOf` is confirmed broken.** Devs must double-validate in `call()` and risk retry loops.
- `Tool.parameters` is **computed once at session init** and never re-read.
- `SpotlightSearchTool` description/schema mismatch makes it unusable with non-Apple models.
- `toolCallingMode` exists in **two places**: `GenerationOptions(toolCallingMode:)` and
  `DynamicProfile.toolCallingMode(_:)`.
- `onToolCall` errors kill the whole turn — no per-call rejection.
- **Guide need:** a tools chapter that treats validation as mandatory, documents `GenerationSchema` /
  `DynamicGenerationSchema` / `@Generable` / `@Guide` equivalences, and covers approval-gate patterns.

### Cluster E — Simulator vs device (the phantom-bug generator)
Threads: 831404, 831448, 831998, 837226, 799951, 797271.
- The simulator **punches out to the host macOS** for inference → SDK/OS version skew produces meaningless `-1` errors.
- **PCC does not work in simulators at all** (177684296).
- `NLContextualEmbedding.load()` also fails in the simulator with
  `filesystem error: in create_directories: Permission denied ["/var/db/com.apple.naturallanguaged/com.apple.e5rt.e5bundlecache"]`.
- **Guide need:** a prominent "test on device" box + a table of what does/doesn't work in the simulator.

### Cluster F — Adapters: build it, ship it, then it's gone
Threads: 805970, 806779, 823001, 823148, 829108, 831314.
- Whole distribution pipeline (Background Assets + Apple hosting + `ba-package foundation-models package` + manifest
  hack) was undocumented, hard-won by devs — **and then discontinued in OS 27.**
- **Guide need:** an explicit "adapters are dead, here is your migration path (Core ML / Core AI / MLX + Background
  Assets)" section, plus the 26.x pipeline for anyone still shipping to 26.

### Cluster G — PCC: eligibility, entitlement, quota opacity
Threads: 809497, 829539, 831998, 833628, 833641, 834652, 834749, 835897, 835974, 836810, 804366.
- Eligibility is a **business** gate (Small Business Program + <2M lifetime first-time downloads), not a technical one,
  and it surprises successful long-time developers.
- Quota API only exposes coarse states (reached / below / approaching) — no numbers, no percentages. **FB23378161**.
- `fatalError` if entitlement is missing.
- Community-recommended architecture: abstract inference behind a protocol; on-device first; PCC as one tier;
  third-party provider as overflow via the `LanguageModel` protocol.
- **Guide need:** a PCC chapter that leads with eligibility, then entitlement, then the fallback architecture.

### Cluster H — App Intents / App Schemas / on-screen content for Siri AI
Threads: 829586, 833643, 833681, 833691, 837249, 838329, 835903, 775988.
- **Custom `AppEntity` types are not enough**: Siri can *discover* custom entities but can only *act* through
  whitelisted schema domains.
- On-screen handoff only works via `@AppEntity(schema: .files.file)` + `FileEntityIdentifier` + `FileRepresentation`.
- Siri prefers automatic screenshots over app-provided entities for "describe this"/"create a note".
- Raw internal errors leak to users: `TypedValueToContentGraphResolutionErrorDomain error 4`.
- **Guide need:** a schema-domains chapter with the discoverability-vs-action distinction stated up front.

### Cluster I — Evaluations is a documentation desert
Threads: 832053, 833729, 833822 — that's the entire forum.
- Swift-only; `ModelJudgeEvaluator` for subjective scoring; can evaluate `PrivateCloudComputeLanguageModel` responses;
  Apple's own recommended use is **regression testing across OS updates** (since there's no model pinning).
- **Completely unanswered:** image-text / VLM evaluation (MobileCLIP2, YOLOE); MLX-vs-AFM performance comparison.
- **Guide need:** basically everything. Highest leverage per word of any topic here.

### Cluster J — Bringing your own model (MLX / Core AI / third-party cloud)
Threads: 831197, 832555, 833627, 833683, 833716, 836264, 838444, 821088.
- `MLXFoundationModels` lives in `mlx-swift-lm` **PR #334** — not discoverable from the docs.
- `ChatCompletionsLanguageModel` has a hardcoded `v1` path bug.
- `CustomSegment` is the escape hatch for non-text returns.
- A `SKILL.md` in foundation-models-utilities exists for building `LanguageModel` conformances.
- MLX tokenizer breakage across versions (`unsupportedTokenizer`, MLX-libraries 2.25.8 → 2.29.1); chat-format LoRA data
  breaks where text-format works.
- **Guide need:** an interop chapter mapping FoundationModels ↔ MLX ↔ Core AI ↔ OpenAI-compatible endpoints.

### Cluster K — Extensions, background, and daemons
Threads: 803444, 810398, 820379, 833575, 833666.
- `SystemLanguageModel` is **out-of-process** → doesn't count against extension memory limits. But **XPC-restricted
  extensions can't use it at all.**
- No NPU priority/entitlement; OS throttles by thermals.
- `continued-processing.gpu` entitlement exists for background GPU work.
- CoreML/Vision in a session-less system extension: "the daemon-safe frameworks list has not been updated in a while."

### Cluster L — Vision/multimodal grounding gaps
Threads: 833783, 833644, 807863, 811714, 838613, 828235, 824639, 837386.
- FM identifies objects but cannot localize them. Apple's answer: go use Vision.
- No published image size/format/token-cost guidance (833783 unanswered).
- `performAll()` does not parallelize `TrackObjectRequest`.

---

## 5. Undocumented limits, error codes, entitlements, gates — quick reference

| Item | Value / behavior | Source thread |
|---|---|---|
| On-device context window | **4096 tokens** ("around 4,000"), not exposed as a constant | 790736, 833642 |
| PCC context window | **32K** — *community-claimed, not Apple-confirmed* | 833642 (non-Apple reply) |
| Token counting API | `tokenCount(for:)`, since **iOS 26.4** | 817502 |
| Usage introspection | `usage` property on `LanguageModelSession.Response` | 833642 |
| Guided-generation schema limits | **None published**; smaller schemas perform better; failure = error, not malformed output | 833642 |
| Image count per prompt | **Unlimited**, bounded by context window | 833642 |
| Image resolution limit | **None set**; framework may resize | 833642 |
| Image downsample size | **896px longest dimension** — *developer inference, UNVERIFIED* | 838613 |
| Image input & routing | Does **not** change which model services the request | 833642 |
| Model version pinning | **Does not exist**; no version-retrieval API | 833642 |
| Concurrency | OS-limited; background throttling on iOS; no priority control | 833642, 833666 |
| Extension memory | `SystemLanguageModel` is out-of-process; free of extension memory limits | 833575 |
| XPC-restricted extensions | **Cannot use FoundationModels at all** | 833575 |
| Background NPU priority | **No entitlement or API** | 833666 |
| `continued-processing.gpu` | Existing entitlement for background GPU tasks | 833666 (OP) |
| PCC in Simulator | **Broken** — known issue **177684296** | 831998 |
| PCC entitlement missing | Triggers **`fatalError`** at runtime | 831998 |
| PCC eligibility | Small Business Program + **<2M first-time downloads** + entitlement | PCC page, 835897, 833641 |
| PCC over threshold | Notified; **6 months** to migrate | PCC page, 833641 |
| PCC cost | **Free** for eligible developers | PCC page |
| PCC + TestFlight | Installs during testing don't count toward 2M | PCC page |
| PCC on watchOS | Requires paired iPhone with AI enabled — *UNVERIFIED* | 834652 |
| Adapters | **Discontinued in OS 27**; toolkit stops at 26.0.0 | 829108, 831314 |
| Adapter entitlement (26.x) | `com.apple.developer.foundation-model-adapter` | 823148 |
| Adapter packaging CLI | `xcrun ba-package foundation-models package --adapter-path --asset-pack-id --output-path --platforms --on-demand` | 823148, 829108 |
| Adapter manifest bug | `"onDemand": null` → Transporter **ITMS-91140**; patch to `{}` | 823148, 829108 |
| Adapter disk leak path | `/private/var/db/AppleIntelligencePlatform/AppModelAssets/` (SIP-protected) | 823001 |
| Adapter leak size | ~100 MB/call, no GC, no dedup | 823001 |
| Leak service | `TGOnDeviceInferenceProviderService` | 823001 |
| Required Device Capability for AI | **Does not exist** | 836810 |
| Guardrail options | `.default`, `.permissiveContentTransformations`; the latter **excludes `Generable`** | 788053, 835777 |
| `.anyOf` guide | **Broken** — Apple reproduced; should do schema listing + prediction-time constraint | 812501 |
| `Tool.parameters` | Computed **once** at session init | 812501 |
| Error type hierarchy | `LanguageModelError`, `LanguageModelSession.Error`, `LanguageModelSession.GenerationError` (**deprecated 27.0**) | 831404 |
| `ModelManagerServices.ModelManagerError` | **Code 1046**, undocumented | 831998 |
| `com.apple.SensitiveContentAnalysisML` | **error 15**, undocumented | 836285 |
| `com.apple.UnifiedAssetFramework` | **Code 5000**, "no underlying assets … for asset set com.apple.modelcatalog" | 838904 |
| `TypedValueToContentGraphResolutionErrorDomain` | **error 4**, leaks to end users through Siri AI | 835903 |
| `TokenGenerationCore.GuidedGenerationError.invalidConfiguration` | `errorMessage: "Tool Choice requires tools"` | 837226 |
| `LanguageModelSession.ToolCallError` | underlying "Failed to parse generated content." | 832534, 833651 |
| watchOS 27 b2 build break | `Unable to resolve module dependency: 'CoreImage'` — "known bug" | 835987 |
| Speech generation API | **None exposed** for the new model; use AVFoundation | 834149 |
| Evaluations language support | **Swift only** | 833729 |
| Shortcuts "Use Model" | **No error detection possible** | 813757 |
| Non-App-Store macOS apps | **Can** use FoundationModels on-device | 832033 |
| WebKit/JS access | No JS interface; bridge via `WKUserContentController` | 833716 |
| macOS 27 codename | **"Golden Gate"** (developer usage in two threads) | 838904, 831998 |
| iOS 27 beta 3 build | **24A5380h**, released July 6 2026 | 837226 |

---

## 6. Feedback (FB) numbers referenced — useful for cross-referencing Apple's tracker

| FB | Subject | Thread |
|---|---|---|
| FB20828230 | Guardrails block crisis-support detection ("one sec" app) | 833614 |
| FB22523518 | Adapter clones under `AppModelAssets` (macOS 26.3.1) | 823001 |
| FB23018652 | App Schemas restrict custom entities/actions | 829586 |
| FB23060822 | `LanguageModelError -1` in Simulator | 831448 |
| FB23061009 | Cannot pattern-match `LanguageModelError` from a stream | 831404 |
| FB23092325 | `onToolCall` error kills the whole turn loop | 833610 |
| FB23378161 | Request for detailed PCC quota numbers | 835974 |
| FB23513774 | iOS 27 model-level refusal regression (health prompts) | 836673 |
| FB23643759 | SpotlightSearchTool "Tool Choice requires tools" | 837226 |
| FB23813341 | `.appEntityIdentifier` + `Transferable` on-screen image handoff | 838329 |
| FB23837262 | `ChatCompletionsLanguageModel` hardcoded `v1` path | 838444 |

---

## 7. Apple-staff identities and behavior patterns (useful for weighting sources)

- **DTS Engineer** — usually signs *"Ziqiao Chen, Worldwide Developer Relations"*; one older post signs *"-J"*.
  Tone: procedural, routes to Feedback Assistant, gives precise API pointers.
- **Frameworks Engineer** — the FoundationModels team. Gives the most technically specific answers (context window,
  DynamicProfiles, historyTransform, transcript mutability, AFM tiers).
- **Apple Designer** — highly active, conversational ("Whelp, that's totally a bug. 🐛"), often does WWDC26 Q&A
  cleanup passes ("Sorry, catching up on unanswered questions"). Made the two most consequential statements:
  adapters discontinued; the simulator punch-out explanation.
- **Engineer** — appears on Evaluations and Spotlight answers.
- **Sla1708 / Sayan Lakhoua** — named Apple account, PCC entitlement.
- **MB-Researcher** — badge status ambiguous in fetches; treat as community unless confirmed.
- **divyaravi11992** — prolific *non-Apple* "Senior iOS Engineer" whose answers sometimes get quoted as if
  authoritative (e.g. the 32K PCC figure). **Do not treat as Apple.**

Recurring Apple move: *"file a Feedback and post the FB number here."* Many threads end there.
Second recurring move during WWDC26 week: deflecting App Intents/Siri questions out of the FM Q&A.

---

## 8. Cross-links for other agents

- **Docs agents:** TN3193 (context window), `support.apple.com/en-us/121115` (AI requirements + language list),
  `developer.apple.com/documentation/foundationmodels/support-languages-and-locales-with-foundation-models`,
  `.../adding-server-side-intelligence-with-private-cloud-compute`,
  `.../evaluations/scoring-with-model-as-judge-evaluators`,
  `.../evaluations/book-tracker-using-evaluations-to-evaluate-an-intelligent-feature`,
  `.../appintents/making-app-entities-available-in-spotlight`,
  `developer.apple.com/documentation/ios-ipados-release-notes/ios-ipados-27-release-notes#Foundation-Models`.
- **WWDC transcript agents:** sessions cited by Apple staff — **wwdc2026/242** ("Build agentic app experiences with the
  Foundation Models framework"), **wwdc2026/339** ("Bring an LLM provider to the Foundation Models framework"),
  **wwdc2026/240**, **345**, **343** (App Schemas / Siri), *"Secure your app: mitigate risks to agentic features"*,
  and WWDC25 *"Meet Foundation Models"* (guided generation).
- **Repo agents:** `github.com/apple/foundation-models-utilities` — verify
  `Sources/FoundationModelsUtilities/LanguageModels/ChatCompletionsLanguageModel.swift` (line ~634),
  `Sources/FoundationModelsUtilities/History/SummarizeHistory.swift`, the `History` directory, the `SkillActivation`
  module, and the **`SKILL.md`** file. Also `github.com/ml-explore/mlx-swift-lm` **PR #334** (`MLXFoundationModels`).
  Community repo `github.com/ricky-stone/FoundationContext`. Commit pinned by a forum link:
  `376ca60e61985369d5067bd3c575bdb6a13f0e1b`.
- **Core AI agent:** confirm that "all on-device Apple Foundation Models are powered by Core AI" and whether AFM 3 Core
  can actually be opened in the **Core AI Debugger** (asked, never answered).
- **Speech agent:** confirm there is genuinely no new TTS API for the AFM 3 speech model.

---

## 9. Source inventory — everything actually read this session

**Local files**
1. `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-and-ai-foundation-models.txt` (287 lines, full)
2. `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-and-ai-topic-apple-intelligence.txt` (211 lines, full)
3. `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-and-ai-topic-evaluations.txt` (30 lines, full)
4. `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-topic-general.txt` (223 lines, full)

**Topic listing pages fetched**
5. `https://developer.apple.com/forums/topics/machine-learning-and-ai/machine-learning-and-ai-foundation-models` (pages 1–7)
6. `https://developer.apple.com/forums/topics/machine-learning-and-ai/machine-learning-and-ai-topic-evaluations`
7. `https://developer.apple.com/forums/topics/machine-learning-and-ai/machine-learning-and-ai-topic-apple-intelligence?page=2`

**Non-forum page fetched**
8. `https://developer.apple.com/private-cloud-compute/`

**Individual threads fetched in full** (`https://developer.apple.com/forums/thread/<id>`)
788053, 790736, 791250, 797271, 803442, 805378, 811620, 812501, 813757, 817502, 820819, 821088, 823001, 823148,
829108, 829539, 829586, 830161, 831197, 831314, 831404, 831448, 831998, 832033, 832053, 832534, 832868, 832910,
833560, 833575, 833610, 833614, 833623, 833625, 833626, 833627, 833638, 833641, 833642, 833643, 833650, 833651,
833652, 833657, 833658, 833666, 833668, 833683, 833692, 833706, 833712, 833716, 833729, 833783, 833822, 834149,
834652, 834749, 835165, 835211, 835777, 835897, 835903, 835927, 835974, 835987, 836264, 836285, 836316, 836673,
836760, 836810, 837226, 837249, 838329, 838444, 838613, 838904.
(78 threads.)

**Web search used once** to locate TN3193 and thread 817502.

---

## 10. Open questions / unverified

1. **PCC context window = 32K?** Only a community claim (833642). Needs doc confirmation.
2. **896px image downsample.** Developer inference in 838613. Never confirmed by Apple. If true it's a critical
   token-budgeting fact.
3. **What is the "Weight List"?** Mentioned as a WWDC26 AI Group Lab "spoiler alert"; thread 833590 asks whether custom
   adapters via the Language Model Protocol could join it. **Zero replies.** Apparently: a list that applies only to
   Siri, not to the PCC language model. Meaning otherwise unknown.
4. **Does the XPC restriction on some extensions also block `SystemLanguageModel`?** Asked in 833575, unanswered.
5. **Is `PrivateCloudComputeLanguageModel` gated behind the user's Apple Intelligence opt-in**, or is there a separate
   availability tier? Asked in 830161, unanswered.
6. **Can AFM 3 Core be opened in the Core AI Debugger?** Asked in 833657, only the "powered by Core AI" half answered.
7. **AFM 3 Core vs AFM 3 Core Advanced** — what actually differs (params, context, modalities, tool reliability)?
   Apple said only "plan to have different models… guidance will evolve over the summer's beta period."
8. **Does `SystemLanguageModel` expose which tier it is?** No version/pinning API per 833642, so presumably no. Needs
   confirmation.
9. **iOS 27 model-level refusal regression (836673)** — no Apple reply as of capture. Is it a model change, a new
   classifier, or a bug? Blocking a shipping App Store health app.
10. **Adapter migration specifics** — Apple says "Core ML or Core AI" but gives no LoRA→Core AI recipe. Is there an
    equivalent of the Adapter Training Toolkit for Core AI?
11. **PCC for non-App-Store/notarized macOS apps** — 832033 confirms on-device works; PCC page's wording implies App
    Store/TestFlight/ad hoc only. Unresolved.
12. **`GenerationOptions(toolCallingMode:)` vs `DynamicProfile.toolCallingMode(_:)`** — are these the same enum? Which
    is preferred in 27? Apple recommended the DynamicProfile form (833692) while a dev used the GenerationOptions form
    (837226).
13. **`.appleIntelligenceNotEnabled` tied to "Hey Siri"/side-button** (835211) — a Frameworks Engineer said FM should
    work without Siri AI in Europe (836760), so at minimum one of these is a bug. Unresolved either way.
14. **Foundation Models topic page 8** was not enumerated.
15. **`SkillActivation`** — what it is, what it needs, why it fails to build. Only that it lives in
    foundation-models-utilities.
16. **`CustomSegment`** — named by Apple (833683) but no signature captured. Needs repo/doc verification.
17. **`DynamicProfiles` vs `DynamicProfile` vs `DynamicProfileModifier`** — three spellings appear in Apple replies;
    exact type names need doc verification.
18. **"phone-a-friend" pattern** and **"session properties"** — named by Apple (833626) as context strategies; no
    definition captured.
19. **`Attachment(_:orientation:)`** signature — captured from a developer's code, not from docs.
20. **MB-Researcher's Apple status** — the 805378 and 803442 answers would be much stronger if that account is Apple.
