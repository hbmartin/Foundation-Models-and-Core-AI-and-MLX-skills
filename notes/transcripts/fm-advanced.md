# FM Advanced — Dynamic Profiles + Instruments Debugging/Profiling

**Research notes (raw). Theme: `fm-advanced`.**
Primary sources: two WWDC26 session transcripts read IN FULL this session, cross-checked against local
mirrored Apple docs and real compiled Swift in the local repo tree.

| Source | Path | Lines | Title (as inferred) |
|---|---|---|---|
| WWDC26 **242** | `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-242.txt` | 195 | "Build agentic app experiences with the Foundation Models framework" (dynamic profiles) |
| WWDC26 **243** | `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-243.txt` | 154 | Debugging & profiling Foundation Models features with Instruments |

Presenters:
- **242** — **Erik** and **Oliver**. Erik opens/closes + orchestration + perf/accuracy; Oliver does the API mechanics.
- **243** — **Erik**, self-described as "an AI Tools Engineer" (243:1).

> ⚠️ **Reconstruction warning.** These are spoken-word caption transcripts. On-screen code was *described*,
> not dictated. Everything in a fenced block below labelled **[RECONSTRUCTED]** is my best-effort
> reassembly from the narration + corroborating local sources; it is NOT verbatim from Apple. Blocks
> labelled **[VERBATIM — <file>]** are copied character-for-character from a file I read this session.

---

# PART 1 — WWDC26 242: Dynamic Profiles

## 1.1 The framing: two problems Dynamic Profiles exist to solve

Erik lays out the design philosophy before any code (242:3–11).

> **242:4–5** — "The first challenge these APIs solve is **context management**. In long running
> sessions, dynamic profiles let you **trim or summarize the transcript** to keep it within the model's
> context window."

> **242:6–8** — "The second problem these APIs solve is **establishing boundaries**. When using multiple
> models, you should design around **capability and cost considerations**. Dynamic profiles give you that
> option."

The most quotable bit of design rationale — worth reproducing in any guide:

> **242:9–10** — "This field is changing **week-to-week**. The primitives that we're introducing are
> designed to be flexible, ensuring it's possible to build **today's abstractions, and tomorrow's**."

> **242:11** — "Dynamic profiles enable **context engineering**, **defining model boundaries**, and can be
> **scaffolded into just about any architecture**."

Read that as Apple explicitly declining to ship an "Agent" type. Dynamic Profiles are deliberately a
*primitive layer*; the opinionated abstractions live in a separately-versioned package (next section).

## 1.2 Foundation Models framework utilities (new open-source Swift package)

> **242:12–14** — "we're announcing a new package; **Foundation Models framework utilities**. Utilities is
> an **open source Swift package** that houses components helpful for building agentic experiences. It
> will be **updated in between OS releases** and give you access to **emerging or experimental patterns**,
> all **backed by dynamic profiles**."

Named contents of the package, gathered from 242 + corroborating sources:

| Component | Evidence |
|---|---|
| Reusable **profile modifiers** for transcript management | 242:86 "We've made a number of useful modifiers available in the new Foundation Models framework utilities package." |
| A **`Skills`** type — "procedural context loading" | 242:137 |
| A **Chat Completions**-standard `LanguageModel` | `transcripts/wwdc2026-241.txt:130` (cross-session); forum thread confirms class name `ChatCompletionsLanguageModel` |
| A **`SkillActivation`** module/framework | Developer Forums thread 835165 (see §5.3) |

Cross-session corroboration (I grepped, did not read 241 in full — another agent owns it):

> **transcripts/wwdc2026-241.txt:130** — "It provides **profile modifiers for transcript management**, a
> **skill API for procedural knowledge loading**, and a **language model that can interface with servers
> using the Chat Completions standard**."

> **transcripts/wwdc2026-241.txt:5** — "The Foundation Models framework, including many of the brand new
> APIs that we're announcing today, **is going open source**! … we're also releasing a new package,
> Foundation Models framework utilities, that will be updated between OS releases…"

**Repo URL (VERIFIED from a forum post, not from the transcript):**
`https://github.com/apple/foundation-models-utilities`
— cited in `forums/machine-learning-and-ai-foundation-models.txt:260`.

## 1.3 The `DynamicProfile` API — what it is

> **242:20** — "With the introduction of the **`LanguageModel` protocol** and
> **`PrivateCloudComputeLanguageModel`**, you now have more models than ever to choose from."

> **242:21** — "**`DynamicProfile`** is a new API that gives you the ability to **switch models within your
> `LanguageModelSession`**, providing you with the flexibility to select the best configuration for the
> task at hand."

> **242:22** — "`DynamicProfile` is **the foundation on which you can build many useful abstractions, such
> as agents or skills**."

Oliver's agenda (242:23): (1) leveraging multiple models → (2) transcript considerations → (3) session
lifecycle events.

### The three composable layers

| Layer | What it is | Transcript evidence |
|---|---|---|
| `DynamicInstructions` | "grouping of relevant tools and instructions together into a single component that can be reused throughout your codebase" (242:40). **Composable** — nesting concatenates. | 242:39–42 |
| `Profile` | "made up of **instructions, tools, and modifiers** for configuring things like the **model, temperature, samplingMode** and more" (242:33) | 242:32–33 |
| `DynamicProfile` | "allows you to declare individual `Profile`s, which represent a **configuration state or agent** in your `LanguageModelSession`" (242:32) | 242:32 |

Cross-check with the local doc mirror agrees and adds a compiler constraint:

> **[VERBATIM — `repos/noemaai-labs__noema-ios/DocumentationforAPIs&SDKs/AppleFoundationModels/DynamicSessions.md:13–17`]**
> ```
> Three composable layers:
>
> * **Dynamic Instructions** — declare what instructions and tools are needed for the current app state; the body re-evaluates before each model request
> * **Profile** — associates Dynamic Instructions with session-level properties like model, temperature, and reasoning level
> * **Dynamic Profile** — orchestrates transitions between multiple domain-specific profiles using conditionals and nesting; a compiler constraint ensures exactly one Profile is active at any time
> ```

And WWDC26 241 (grep, cross-session):
> **transcripts/wwdc2026-241.txt:97** — "The important thing to understand is that a **`DynamicProfile`
> resolves to a single active `Profile` at any given time**. You use **conditionals** to pick which
> `Profile` is active, and the framework handles the transition for you."

### ⚠️ Naming discrepancy: `DynamicProfile` vs `LanguageModelSession.DynamicProfile`

Both transcripts and the doc mirror say bare `DynamicProfile` / `Profile`. **Real compiled Swift in the
local tree uses the *nested* spelling.** This is the single most likely place a guide gets the code wrong.

> **[VERBATIM — `repos/ml-explore__mlx-swift-lm/IntegrationTesting/IntegrationTestingTests/MLXFoundationModelsIntegration/ToolCalling/StructuredToolOutputSessionTests.swift:47–54`]**
> ```swift
> @available(iOS 27.0, macOS 27.0, visionOS 27.0, *)
> private struct StructuredToolOutputProfile: LanguageModelSession.DynamicProfile {
>     let model: MLXLanguageModel
>
>     @SessionProperty(\.structuredToolOutputCallCount)
>     var toolCallCount
>
>     var body: some LanguageModelSession.DynamicProfile {
> ```

Independently corroborated by a third party who says they compiled against the macOS 27.0 SDK:

> **[VERBATIM — `repos/john-rocky__coreai-model-zoo/knowledge/dynamic-profiles-local-models.md:19–38`]**
> ```
> ## The API surface (verified against the macOS 27.0 SDK)
>
> ```swift
> struct RoutingProfile: LanguageModelSession.DynamicProfile {
>     let router: Router            // your state: which profile is active
>     let fast: KitLanguageModel
>     let smart: KitLanguageModel
>
>     var body: some LanguageModelSession.DynamicProfile {
>         if router.route == .smart {
>             Profile { Instructions("You are the expert.") }
>                 .model(smart).maximumResponseTokens(384)
>         } else {
>             Profile { Instructions("You are fast triage.") }
>                 .model(fast)
>         }
>     }
> }
> let session = LanguageModelSession(profile: RoutingProfile(...))
> ```
> ```

**Working conclusion:** the protocol is `LanguageModelSession.DynamicProfile`; `Profile` appears
un-nested at use sites (probably via a typealias or because it's resolved in the result-builder scope).
Guides should use the nested spelling for the protocol conformance and `some LanguageModelSession.DynamicProfile`
for the `body` type. Mark bare `DynamicProfile` as "as spoken / as written in article prose."

## 1.4 The running example: the Origami / Craft app

242 and 243 use the *same* app, described slightly differently — worth noting because guide examples will
otherwise contradict each other.

**242's version (242:25–28):**
> "I'm working on a craft app called **Origami** which can produce **both origami and crochet tutorials**.
> Here, the user will **upload images** and our app will help them **brainstorm ideas using the image as
> inspiration**. The user can provide feedback on the **shortlist of ideas** before a **tutorial** is
> generated for the selected concept. While the user works through the tutorial, they can upload
> **in-progress photos** and get **advice on their technique**."

**242's phase → profile map:**

| Phase | Model chosen | Modifier(s) | Rationale (verbatim) |
|---|---|---|---|
| `brainstorming` | `PrivateCloudComputeLanguageModel` | `.temperature(1)` | 242:45 "brainstorming requires **both a broad knowledge of crafts and creative thinking**"; 242:47 "set the temperature to **1**, to allow the model to produce more **creative** responses" |
| `planning` | `PCCLanguageModel` | `.reasoningLevel(.deep)` | 242:51 "requires **in-depth knowledge of crafts**"; 242:54 "Since generating a tutorial is complex, we'll set it to **deep**" |
| `reviewing` | `SystemLanguageModel` | `.historyTransform { … }` (added later) | 242:56 "**To save on unnecessary server calls**, this makes use of `SystemLanguageModel`" |

> **242:52–53** — "We'll also configure **`reasoningLevel`**, which is **a capability available to most
> server models**. This controls the model's capacity to think through the problem before responding."

Note the model name inconsistency inside 242 itself: `PrivateCloudComputeLanguageModel` at 242:45 but
"PCCLanguageModel" at 242:51 and 242:65. The docs mirror only ever uses
**`PrivateCloudComputeLanguageModel`**. Treat "PCCLanguageModel" as caption shorthand.

**243's version (243:45–51):**
> "a **crafting companion app** where you can keep a **journal of your craft projects**… **This feature
> uses two sets of instructions**: one for **brainstorming ideas**, and a second for **tutorial
> generation**. The brainstorming instructions include **two tools**: a **`GenerateCraftIdeaTool`** and a
> **`SwitchToTutorialModeTool`**. **Both** sets of instructions use the **server model on Private Cloud
> Compute**, one for quick idea generation and the other to generate more detailed tutorials."

The Apple sample app for this is documented in the local mirror as **"Origami: Crafting a dynamic tutorial
for Apple Intelligence"** (`.../AppleFoundationModels/Origami.md`), with **three** modes — `.brainstorm`,
`.tutorial`, `.term` — rather than 242's three of brainstorm/planning/reviewing. Note the drift; the
sample's `.term` mode ("fast on-device lookups for origami terminology") never appears in 242.

## 1.5 `DynamicProfile` — reconstructed declaration

Narration path (242:34–48):
1. 242:35 — "we have an **`Observable` class called `CraftOrchestrator`** that will track the different
   phases of the app."
2. 242:37 — first profile has "some **instructions** explaining its goal and a **tool for generating
   titles**."
3. 242:38 — "let's also include some **additional instructions and tools but only when the user is working
   on an origami project**."
4. 242:39–42 — extract that into `OrigamiExpert: DynamicInstructions`.
5. 242:43 — "we've created **`BrainstormFacilitator`** to hold our profile's instructions."
6. 242:44 — "Now we can **clean up our brainstorming profile** using the new declaration."

**[RECONSTRUCTED — 242:34–57]**
```swift
@Observable
final class CraftOrchestrator {
    enum Mode { case brainstorming, planning, reviewing }
    var mode: Mode = .brainstorming
    var craftKind: CraftKind = .origami          // .origami | .crochet
}

// Step 1 — a reusable DynamicInstructions bundling origami knowledge + its tools (242:39–42)
struct OrigamiExpert: DynamicInstructions {
    var body: some DynamicInstructions {
        Instructions {
            "You are an expert in traditional and modern origami."
            "Explain folds using standard origami terminology."
        }
        FoldLookupTool()
        PaperSelectionTool()
    }
}

// Step 2 — a second DynamicInstructions that NESTS the first (242:42–43)
struct BrainstormFacilitator: DynamicInstructions {
    var craftKind: CraftKind

    var body: some DynamicInstructions {
        Instructions {
            "Help the person brainstorm craft project ideas from the photos they share."
            "Offer a short list of distinct concepts."
        }
        GenerateTitleTool()

        // Conditional content LAST — see §1.11 for why (KV cache).
        if craftKind == .origami {
            OrigamiExpert()
        }
    }
}

// Step 3 — the DynamicProfile that swaps between agents (242:44–57)
struct CraftProfile: LanguageModelSession.DynamicProfile {
    var orchestrator: CraftOrchestrator

    var body: some LanguageModelSession.DynamicProfile {
        switch orchestrator.mode {
        case .brainstorming:
            Profile(model: PrivateCloudComputeLanguageModel()) {
                BrainstormFacilitator(craftKind: orchestrator.craftKind)
            }
            .temperature(1)

        case .planning:
            Profile(model: PrivateCloudComputeLanguageModel()) {
                TutorialPlanner()
            }
            .reasoningLevel(.deep)

        case .reviewing:
            Profile(model: SystemLanguageModel.default) {
                TechniqueReviewer()
            }
        }
    }
}
```

> **242:42** — "DynamicInstructions are also **composable** so **nesting `OrigamiExpert` inside another
> `DynamicInstructions` body will concatenate the instructions and tools together**."

### Wiring it to a session

> **242:58** — "To make use of `DynamicProfile` in your session, it's as simple as using the **new
> `LanguageModelSession` initializer**."

**[VERBATIM — `.../AppleFoundationModels/DynamicSessions.md:81`]**
```swift
let session = LanguageModelSession(profile: AppProfile())
```

The doc mirror also names a *second* initializer used for restoring:
`init(profile:history:)` — see `.../OptimizingKV.md:38` and `.../DynamicSessions.md:153–159`:
```swift
let session = LanguageModelSession(
    profile: AppProfile(),
    history: savedTranscript
)
session.prewarm()
```

### Body re-evaluation semantics — **critical footgun**

> **242:59** — "Note that **the body of a `DynamicProfile` is re-evaluated each time the model is
> prompted**, so as the app moves between each mode, **the persona of the `LanguageModelSession`
> changes**."

> **242:60–62** — "You can think of this as **swapping hats, or switching agents**. You can move from
> brainstorming to planning, to reviewing. **All by changing the mode**."

243 states the same for `DynamicInstructions`:
> **243:8–9** — "`DynamicInstructions` lets you specify **exactly which instructions and tools the model
> can access**. It **re-evaluates before every request**, so the model always has the right context for
> the task at hand."

⚠️ **The transcripts say "each time the model is prompted" — a third-party measurement says it is more
than once per turn.** This matters enormously for purity:

> **[VERBATIM — `repos/john-rocky__coreai-model-zoo/knowledge/dynamic-profiles-local-models.md:48–51`]**
> ```
> 1. **The `body` is re-evaluated multiple times per turn** (7 evaluations for 3 turns). The
>    framework reads it more than once to gather instructions and resolve the model. **Keep the
>    body pure** — read your route variable there, never mutate state. Imperative work goes in
>    lifecycle modifiers (`onResponse`, …), which fire once at their boundary.
> ```

**Guide rule to carry forward: `body` must be pure. All mutation goes in lifecycle modifiers.**

## 1.6 Transcript & "history" — the context surface

> **242:64** — "it's important to consider that **each model may have different context size limits**."

> **242:66–68** — "When moving between models, you may need to **trim unnecessary entries to stay within
> the context size**. But that's not the only reason for adjusting the model's context. You can also
> **improve the model's focus by removing irrelevant entries**, or **redact private information from
> existing entries when moving to a less private model**."

That last clause is the privacy-boundary argument for `historyTransform` — on-device → PCC is a privacy
hop, and 242 explicitly recommends redacting on the way out.

> **242:69–72** — "**The transcript is `LanguageModelSession`'s representation of the model's context.**
> `DynamicInstructions` offers **one way** to modify the transcript. More specifically, it allows
> **modifying the instructions entry**. For updating the remaining entries, we'll use **a window into the
> transcript called "history"**."

So the mental model is:

```
transcript  =  [ instructions entry ]  +  history (everything else)
                    ^                        ^
            DynamicInstructions        historyTransform / @SessionProperty(\.history)
```

> **242:73** — "**Dropping tool calls is one easy way to trim history.**"

### `historyTransform(_:)`

> **242:75** — "**`historyTransform` can be applied to a profile to transform the history prior to
> prompting the model.**"

> **242:76** — "This is the opportune time to **filter out entries that may not be necessary for the
> request**."

> **242:77** — "Applying a transformation on our 'reviewing' profile helps **keep the transcript within the
> on device model's context size**."

**The single most important property (242:78–80):**
> "**Transforms don't permanently mutate the session's transcript. Instead, they're local transformations
> applied prior to prompting the model.** This means **you don't need to worry about losing context that
> may become relevant at a later point**."

**[RECONSTRUCTED — 242:73–77]** — "drop tool calls" transform on the reviewing profile:
```swift
case .reviewing:
    Profile(model: SystemLanguageModel.default) {
        TechniqueReviewer()
    }
    .historyTransform { history in
        history.filter { entry in
            switch entry {
            case .toolCall, .toolOutput: return false
            default:                     return true
            }
        }
    }
```

**Closure signature — NOT stated in 242.** From the doc mirror the closure takes and returns "history":

**[VERBATIM — `.../DynamicSessions.md:137–145`]**
```swift
Profile {
    // ...
}
.historyTransform { history in
    // Remove debug metadata — same token count, preserves cache
    clearDebugFromHistory(history)
}
```

And the `@SessionProperty(\.history)` declaration in the same doc is typed:
**[VERBATIM — `.../DynamicSessions.md:118–119`]**
```swift
@SessionProperty(\.history)
var history: [Transcript.Entry]
```

⇒ **Best inference (mark UNVERIFIED):** `historyTransform` is
`(( [Transcript.Entry] ) -> [Transcript.Entry]) -> Self`, possibly `async`/`throws`, possibly
`@Sendable`. The doc-page URL Apple gives is
`/documentation/foundationmodels/languagemodelsession/dynamicprofile/historytransform(_:)`
(`.../OptimizingKV.md:104`) — which **again confirms the nested `LanguageModelSession.DynamicProfile`
spelling**.

A security-oriented third-party note adds a behavior neither transcript states:

> **[VERBATIM — `repos/john-rocky__coreai-model-zoo/knowledge/agentic-security-checklist.md:112–116`]**
> ```
> - **`.historyTransform`** — fires *before the transcript is rendered to the model*, on every new user
>   request **and every loop iteration**. Modifies the **tail** of the transcript. → the place to apply
>   **spotlighting** (add delimiters to untrusted tool outputs) and **PII redaction** (swap sensitive spans
>   for a placeholder). ⚠️ **Transforms are scoped to the current inference only** — not visible to the
>   next call, so re-apply every iteration.
> ```
(Attributed there to WWDC26 347 "Secure your app: mitigate risks to agentic features" — a session I did
not read; treat the "every loop iteration" claim as **secondary**.)

## 1.7 Custom modifiers: `DynamicProfileModifier`

> **242:81–82** — "Our `historyTransform` has a lot going on. Let me show you how we can use **custom
> modifiers** to hide the complexity of our transform."

> **242:83** — "First, we'll declare **a new type that conforms to `DynamicProfileModifier`** and apply our
> `historyTransform`."

> **242:84–85** — "We can then **make it available for reuse by implementing an extension on
> `DynamicProfile`**. Any new Profiles that would benefit from reducing context can now utilize the new
> modifier."

> **242:88** — "**Custom modifiers are a great way to build reusable configuration for your
> declarations.**"

**[RECONSTRUCTED — 242:83–85]** — this is a SwiftUI `ViewModifier`-shaped API:
```swift
struct ReducedContext: DynamicProfileModifier {
    func body(content: Content) -> some LanguageModelSession.DynamicProfile {
        content
            .historyTransform { history in
                history.filter { entry in
                    switch entry {
                    case .toolCall, .toolOutput: return false
                    default:                     return true
                    }
                }
            }
    }
}

extension LanguageModelSession.DynamicProfile {
    func reducedContext() -> some LanguageModelSession.DynamicProfile {
        modifier(ReducedContext())
    }
}

// use site
Profile(model: SystemLanguageModel.default) { TechniqueReviewer() }
    .reducedContext()
```
The `.modifier(_:)` entry point is corroborated:
> **`repos/john-rocky__coreai-model-zoo/knowledge/dynamic-profiles-local-models.md:40–44`** lists the
> modifier set as: "`.model`, `.temperature`, `.samplingMode`, `.maximumResponseTokens`,
> `.reasoningLevel`, `.toolCallingMode`, `.historyTransform`, `.transcriptErrorHandlingPolicy`,
> lifecycle `.onActivate/.onDeactivate/.onPrompt/.onResponse/.onToolCall/.onToolOutput`, and
> **`.modifier(_:)`**."

⚠️ The exact `DynamicProfileModifier` requirement name (`body(content:)`? associated `Content`?) is
**UNVERIFIED** — 242 only says "conforms to `DynamicProfileModifier` and apply our historyTransform".

## 1.8 Lifecycle modifiers

> **242:91–92** — "At certain points in the session, you may need to **summarize earlier entries from the
> existing transcript to reclaim context**. **Doing this after each model's response provides a clear
> boundary in the session's lifecycle.**"

> **242:94** — "**Lifecycle modifiers provide access to your profile's progress by giving you the
> opportunity to run imperative code directly in your profile declaration.** This can be useful for
> **updating state external to your session, like reflecting progress in UI**. But it's also useful for
> **internal state updates, like changing the mode in our craft profile or modifying the session's
> history**."

242 names **only `onResponse`** explicitly (242:97). The complete set comes from the doc mirror:

**[VERBATIM — `.../DynamicSessions.md:92–101`]**
```
## Life Cycle Modifiers

Attach callbacks to profile events:

* `onActivate()` — runs when this profile becomes active
* `onDeactivate()` — runs when this profile becomes inactive
* `onPrompt()` — runs after a user prompt appends to the transcript
* `onResponse()` — runs after the model produces a response
* `onToolCall()` — runs when the model invokes a tool
* `onToolOutput()` — runs when a tool produces output
```

Real compiled usage of `.onToolCall` with a **zero-argument trailing closure**:
**[VERBATIM — `.../StructuredToolOutputSessionTests.swift:62–65`]**
```swift
            .model(model)
            .toolCallingMode(.required)
            .onToolCall {
                toolCallCount += 1
            }
```

But the security checklist sketches a **one-argument** form with a `call` parameter carrying `toolName`,
and says throwing from it **blocks the tool**:
> **[VERBATIM — `repos/john-rocky__coreai-model-zoo/knowledge/agentic-security-checklist.md:99–111`]**
> ```
> - **`.onToolCall`** — fires when the model emits a tool call, **before the executor runs it**. *If the
>   callback throws, the tool never runs* and control returns to the loop. → **the single chokepoint for
>   confirmations.** …
>   ```
>   // sketch from 347
>   profile.onToolCall { call in
>       guard call.toolName == "OrderTea" else { return }   // others run untouched
>       guard await confirmWithUser(call) else { throw CancelledByUser() }  // throw == block
>   }
>   ```
> ```
⇒ Likely **overloads**: `onToolCall { }` and `onToolCall { call in }`, possibly `async throws`.
**UNVERIFIED** which arities exist.

**Lifecycle ordering** (third-party measurement, not in either transcript):
> **`.../dynamic-profiles-local-models.md:53–55`** — "**Lifecycle order on a switch** is
> `old.onDeactivate → new.onActivate → onPrompt → onResponse`. First entry into a profile fires
> `onActivate` **before** `onPrompt`."

## 1.9 Session properties — `@SessionProperty` / `@SessionPropertyEntry` / `SessionPropertyValues`

> **242:98–99** — "You'll notice this is also making use of another new concept: **session properties**.
> **Session properties allow you to define state that's accessible from any `Tool` or `Profile`.**"

### The built-in `history` property

> **242:100–101** — "**The `history` property that we just used is a built-in property provided by the
> framework.** It **captures the session's history** and can be used as **an alternative to
> `historyTransform` for updating the transcript**."

**The decision rule — quote this verbatim in any guide (242:102–103):**
> "**Keep in mind that the `history` property is lossy and its changes will be reflected across all
> profiles in the session. For lossless transformations targeted to specific profiles, you should prefer
> `historyTransform`.**"

| | `historyTransform` | `@SessionProperty(\.history)` |
|---|---|---|
| Mutates real transcript? | **No** — "local transformations applied prior to prompting the model" (242:79) | **Yes** — "lossy" (242:102) |
| Scope | **Per-profile**, targeted | **All profiles in the session** (242:102) |
| Reversible? | Yes — original context still there (242:80) | No |
| When to use | Focus/redaction/trim for one profile | Consolidation/summarization at a boundary |
| KV cache | Stateless & shape-preserving transforms can preserve cache (`OptimizingKV.md:106`) | Invalidates from the point of change (`OptimizingKV.md:119`) |

### Declaring custom properties

> **242:104–108** — "In addition to `history`, you can also **create your own session properties**. Let's
> create a new property to store our **conversation summary** when `onResponse` is called. **You can
> declare properties using the `@SessionPropertyEntry` macro within an extension on
> `SessionPropertyValues`.** **All session properties are mutable and must have an initial value.** Here,
> we've declared our **summary as an optional string**."

> **242:109–111** — "**Each `Profile` can now read the value of the summary by accessing the session
> property** that we just declared. We'll **include the summary in our profile's instructions** to ensure
> they have the context on the transcript entries that were dropped. **Any profile can write to the
> property and changes will be visible across the session.**"

**[VERBATIM — `.../StructuredToolOutputSessionTests.swift:14–18`]** — real compiled declaration:
```swift
@available(iOS 27.0, macOS 27.0, visionOS 27.0, *)
extension SessionPropertyValues {
    @SessionPropertyEntry
    var structuredToolOutputCallCount: Int = 0
}
```
Note: **no parentheses** on `@SessionPropertyEntry` in real code (the doc mirror writes
"`@SessionPropertyEntry()` macro" at `DynamicSessions.md:131` — minor discrepancy, prefer the compiled form).

**[VERBATIM — `.../StructuredToolOutputSessionTests.swift:51–52`]** — reading it in a profile:
```swift
    @SessionProperty(\.structuredToolOutputCallCount)
    var toolCallCount
```

**[VERBATIM — `.../StructuredToolOutputSessionTests.swift:120`]** — reading it from *outside*, off the session:
```swift
        #expect(session.properties.structuredToolOutputCallCount == 1)
```
⇒ **`LanguageModelSession.properties` exists** and is keyed by the same property name. This is a real API
surface neither transcript mentions.

**[RECONSTRUCTED — 242:97, 104–110]** — the summarize-at-response-boundary pattern:
```swift
extension SessionPropertyValues {
    @SessionPropertyEntry
    var conversationSummary: String? = nil
}

struct CraftProfile: LanguageModelSession.DynamicProfile {
    var orchestrator: CraftOrchestrator

    @SessionProperty(\.history)             var history
    @SessionProperty(\.conversationSummary) var summary

    var body: some LanguageModelSession.DynamicProfile {
        Profile {
            Instructions {
                "Help the person with their craft project."
                if let summary {
                    "Summary of earlier conversation: \(summary)"
                }
            }
        }
        .onResponse {
            // Reclaim context at the response boundary (242:92, 242:97)
            summary = await summarize(history)
            history = Array(history.suffix(4))
        }
    }
}
```

> **242:112** — "**Now let me produce a conversation summary for you.**" (an in-demo joke — the model
> summarizes the talk itself.)

**Oliver's three-line recap (242:113–115), verbatim:**
> - "Use **lifecycle modifiers** to run code at specific points in the session."
> - "Use the **`history` property** to update the session's history **for all profiles**."
> - "Use **custom session properties** for storing state that's shared by all session components."

## 1.10 Orchestration patterns: baton-pass and phone-a-friend

> **242:119–120** — "We like to refer to these patterns as **baton-pass** and **phone-a-friend**.
> **Baton-pass is a collaboration and phone-a-friend is a consultation.**"

### Baton-pass

Three ingredients (242:122–125):
> - **242:122** — "there are **two or more profiles**, typically **each leveraging different models**."
> - **242:123** — "There also needs to be **a variable that controls which profile is active**."
> - **242:124** — "Finally, we **give each profile a tool that allows the model to set that variable**."

Worked example (242:126–127):
> "If we're currently brainstorming and ask **how to fold a crane**, the **brainstorm profile will call a
> tool to pass the baton to the tutorial profile**. **A tool output signals a successful handoff**, and
> the **tutorial profile produces the final answer**."

**Defining attributes (242:128), verbatim:**
> "the **full transcript history is visible to both profiles**, and … **the profile that receives the baton
> can carry it across the finish line and provide the final response**."

**[RECONSTRUCTED — 242:122–128]**
```swift
struct SwitchToTutorialModeTool: Tool {
    let name = "switchToTutorialMode"
    let description = "Switch the app into tutorial mode for a chosen craft."

    @Generable
    struct Arguments {
        @Guide(description: "The craft the person selected")
        var craft: String
    }

    let orchestrator: CraftOrchestrator

    func call(arguments: Arguments) async throws -> String {
        orchestrator.mode = .planning            // flip the controlling variable
        orchestrator.selectedCraft = arguments.craft
        return "Switched to tutorial mode for \(arguments.craft)."   // "tool output signals a successful handoff"
    }
}
```
(243:125 confirms the real sample passes the craft as a tool argument: "That inference resulted in a tool
call to **`switchToTutorialMode`, passing the selected craft as an argument**.")

### Phone-a-friend

> **242:130–131** — "you also rely on **tool calling**. The key difference is that **instead of toggling a
> variable, the tool spawns a short-lived session**."

> **242:132–134** — "If we ask for **a fun project for kids**, the model may reason that **it needs a title
> for the project**, and call its phone-a-friend tool **to consult with the title profile**. The
> phone-a-friend tool **spawns a new session with an independent transcript, prompts it, and then delivers
> the response back as tool output**. **The child session disappears**, and the **parent session produces
> the final response**."

**Defining attributes (242:135), verbatim:**
> "the **transcripts for each profile are isolated**, and … the **parent profile is always responsible for
> giving the final answer**."

**[RECONSTRUCTED — 242:130–135]**
```swift
struct TitleConsultantTool: Tool {
    let name = "generateTitle"
    let description = "Consults a specialist to name a craft project."

    @Generable
    struct Arguments {
        @Guide(description: "A short description of the project")
        var projectDescription: String
    }

    func call(arguments: Arguments) async throws -> String {
        // A NEW session with an INDEPENDENT transcript. It dies at the end of this call.
        let child = LanguageModelSession(profile: TitleProfile())
        let response = try await child.respond(to: arguments.projectDescription)
        return response.content              // delivered back as tool output
    }
}
```

### Comparison table

| | **Baton-pass** | **Phone-a-friend** |
|---|---|---|
| Nature (242:120) | Collaboration | Consultation |
| Mechanism | Tool flips the active-profile variable | Tool spawns a **short-lived child session** |
| Transcript | **Shared** — full history visible to both (242:128) | **Isolated** per profile (242:135) |
| Who answers | **The receiving profile** (242:128) | **Always the parent** (242:135) |
| Lifetime | Both profiles persist in one session | Child session "disappears" (242:134) |

> **242:136–137** — "Baton-pass and phone-a-friend are good tools to have in your belt, **but there are
> other options as well**. For example, the **Foundation Models framework utilities package houses a
> `Skills` type**, which you may be familiar with as **a popular pattern for procedural context
> loading**."

**Third-party field report — this is a real gotcha worth surfacing:**
> **`repos/john-rocky__coreai-model-zoo/knowledge/dynamic-profiles-local-models.md:70–77`** — "242's
> baton-pass flips the route from inside a **tool** the model calls. On the kit's upstream engine that
> path is unreliable: small/thinking models emit tool-call JSON the framework rejects with
> `GenerationError.decodingFailure`… The reliable 'the model decides' channel is **guided generation**."
> (Applies to third-party `LanguageModel` providers, **not** to Apple's own models. Note the caveat.)

## 1.11 Tool calling mode

> **242:138–139** — "we're going to look at **a new knob you can use to exert control over when tool calls
> happen — Tool calling mode**. Tool calling mode has **three options: `allowed`, `disallowed`, and
> `required`**."

| Case | Semantics (verbatim) | When to use (verbatim) |
|---|---|---|
| `.allowed` **(default)** | 242:140–141 "The **default value** is 'allowed', which is **the existing behavior**. The model **may produce a tool call or it may respond directly**." | 242:142 "This is the option to use when **you just don't know if tools will be necessary or not, which is the most common case**." |
| `.disallowed` | 242:143 "**prevents the model from calling tools**." | 242:144 "helpful if **the user navigates into a part of your app where the session's tools are known to be irrelevant**." |
| `.required` | 242:145 "**the model can only call tools**." | 242:146 "particularly useful in **agentic systems that represent all actions as tool calls**." |

### Two ways to set it

> **242:147** — "**If you're using profiles, you can specify tool calling mode with a modifier.**"
> **242:148** — "**If you're not using a profile, tool calling mode can be set via `GenerationOptions` when
> calling `respond(to:)`.**"

**[VERBATIM — `.../StructuredToolOutputSessionTests.swift:62–74`]** — modifier form, real compiled code:
```swift
            .model(model)
            .toolCallingMode(.required)
            .onToolCall {
                toolCallCount += 1
            }
        } else {
            Profile {
                Instructions {
                    "Use the latest tool output. Return its requiredToken field exactly and no other text."
                }
            }
            .model(model)
            .toolCallingMode(.disallowed)
```

**[VERBATIM — `forums/machine-learning-and-ai-foundation-models.txt:170`]** — `GenerationOptions` form, from
a real developer's code:
```swift
let response = try await session.respond(to: prompt, options: GenerationOptions(toolCallingMode: .required))
```

**Exact type: `GenerationOptions.ToolCallingMode`, with a `.kind` sub-property.**
**[VERBATIM — `repos/ml-explore__mlx-swift-lm/Libraries/MLXFoundationModels/ToolCalling/ToolCallingModeResolution.swift:14–45`]**
```swift
    static func resolve(
        _ mode: GenerationOptions.ToolCallingMode?
    ) -> GenerationOptions.ToolCallingMode {
        mode ?? .allowed
    }

    static func usesAllowedBehavior(
        _ mode: GenerationOptions.ToolCallingMode
    ) -> Bool {
        switch mode.kind {
        case .allowed:
            return true
        case .required, .disallowed:
            return false
        @unknown default:
            return true
        }
    }

    static func enabledToolDefinitions(
        for mode: GenerationOptions.ToolCallingMode,
        from definitions: [Transcript.ToolDefinition]
    ) throws -> [Transcript.ToolDefinition] {
        if usesAllowedBehavior(mode) {
            return definitions
        }
        if mode.kind == .disallowed {
            return []
        }
        guard !definitions.isEmpty else { throw Error.requiredToolsMissing }
        return definitions
    }
```
Facts extracted: `ToolCallingMode` is **nested under `GenerationOptions`**, is **not** a bare frozen enum
(it has `.kind`, and the switch needs `@unknown default` ⇒ the `kind` enum is **non-frozen / resilient**),
default is `.allowed`, and `.disallowed` is implemented by **sending zero tool definitions**.
The doc mirror also lists a top-level `ToolCallMode` doc page
(`/documentation/foundationmodels/toolcallmode`, `Overview.md:127–128`) — **name discrepancy**
(`ToolCallMode` vs `ToolCallingMode`); the compiled code says `ToolCallingMode`.

### ⚠️ The `.required` while-loop footgun

> **242:149–150** — "**Here's the most important thing to remember. When tool calling is required, the
> model is essentially in a while loop — it is your job to ensure that there is an exit condition of some
> kind.**"

**Escape hatch #1 — conditionalize the mode on a variable (242:151–152):**
> "One good option is to **conditionalize the tool call mode on a variable**. Here, we're **requiring tool
> calls until the model calls the database tool**."

This is *exactly* the shape of the real compiled test in the local tree — required until a counter moves,
then disallowed:
**[VERBATIM — `.../StructuredToolOutputSessionTests.swift:54–76`]**
```swift
    var body: some LanguageModelSession.DynamicProfile {
        if toolCallCount == 0 {
            Profile {
                Instructions {
                    "Call the lookup tool once. After it returns, answer with the value of its requiredToken field exactly."
                }
                StructuredLookupTool()
            }
            .model(model)
            .toolCallingMode(.required)
            .onToolCall {
                toolCallCount += 1
            }
        } else {
            Profile {
                Instructions {
                    "Use the latest tool output. Return its requiredToken field exactly and no other text."
                }
            }
            .model(model)
            .toolCallingMode(.disallowed)
        }
    }
```
This is the **canonical reference implementation of 242:151–152** and should anchor any guide section on
`.required`.

**Escape hatch #2 — a throwing "final answer" tool (242:153–154):**
> "A second, **more forceful** option is to **equip your model with a final answer tool that throws an
> error**. **Throwing an error aborts the tool calling loop and immediately returns control flow to you.**"

**[RECONSTRUCTED — 242:153–154]**
```swift
struct FinalAnswerTool: Tool {
    let name = "finalAnswer"
    let description = "Call this with your final answer when the task is complete."

    struct Done: Error { let answer: String }

    @Generable
    struct Arguments { var answer: String }

    func call(arguments: Arguments) async throws -> String {
        throw Done(answer: arguments.answer)   // aborts the loop, control returns to caller
    }
}
```

## 1.12 Transcript error handling policy + mutable `transcript`

> **242:155** — "**By default, when you throw an error from a tool, or when you cancel a response, your
> session's transcript will roll back to its previous state.**"

> **242:156–157** — "For advanced use cases where you want to **allow cancelling part way through a
> response and then resuming again**, you need to **keep your transcript in state after an error**. We've
> added new API to enable this."

> **242:158–159** — "If you're using profiles, you can now set **`transcriptErrorHandlingPolicy`** using a
> **modifier**. If you're not using a profile, you can **set it directly on your session**."

> **242:160–162** — "The two options are **`.revertTranscript`** and **`.preserveTranscript`**."
> (the caption splits these as `".` / `revertTranscript"` — reassembled.)

> **242:163–164** — "When using **`.preserveTranscript`**, **the onus is on you to put your transcript back
> into a good state if you intend to continue using your session.**"

> **242:165–167** — "To facilitate that, **the `transcript` property on session is now mutable**. Remember
> though, **you can only modify the transcript when the session's `isResponding` property is `false`**.
> **Attempting to mutate the transcript during a response is a programmer error.**"

⚠️ "Programmer error" in Apple parlance = **trap / crash**, not a thrown Swift error. Guard every
`session.transcript = …` with `!session.isResponding`.

**[RECONSTRUCTED — 242:158–167]**
```swift
// Profile form
Profile { AgentInstructions() }
    .transcriptErrorHandlingPolicy(.preserveTranscript)

// Non-profile form
let session = LanguageModelSession(tools: [...])
session.transcriptErrorHandlingPolicy = .preserveTranscript   // UNVERIFIED: property vs. init param

// Repair after an abort
guard !session.isResponding else { return }   // mutating while responding is a programmer error
session.transcript = repaired(session.transcript)
```

| Policy | Behavior |
|---|---|
| `.revertTranscript` | **Default** (242:155 describes the default as rollback). Tool throw / cancellation ⇒ transcript rolls back to previous state. |
| `.preserveTranscript` | Partial response and preceding entries stay. **You** must repair before reuse (242:164). Enables cancel-then-resume (242:156). |

## 1.13 Performance: KV caches

> **242:168–169** — "we need to talk about the implications of **mutating the transcript on performance and
> accuracy**. **Key-value, or KV caches are an important optimization mechanism in large language models
> and they can be invalidated by transcript mutations.**"

**The rule (242:170–171), verbatim:**
> "Generally, **appending to the transcript preserves the KV cache, and minimizes the time-to-first-token**.
> If you **rewrite history by removing entries, changing the attached tools, or updating the instructions**,
> that will **typically trigger a cache invalidation, and can increase latency**."

**The "training wheels" quote — the single best framing of the 2026 API change (242:172–174):**
> "Now, we **didn't talk about this last year** because we **intentionally shaped `LanguageModelSession`
> APIs to be append only**. By default, they ensured optimal use. But **this year, we're taking the
> training wheels off**, so to say."

> **242:175** — "It's important to understand that **different models have different caching behavior and
> the only way to be certain is by measuring**."

> **242:176–177** — "The best way to do that is the **upgraded Foundation Models Instrument in Xcode**. For
> more about **detecting cache invalidations with Instruments**, make sure to check out our video on
> debugging and profiling." *(= session 243.)*

### Cross-check: the local KV doc goes far beyond 242

`repos/noemaai-labs__noema-ios/DocumentationforAPIs&SDKs/AppleFoundationModels/OptimizingKV.md` is the
written companion. It **agrees** with 242 on every point and adds concrete mechanics:

- **Token layout** (`OptimizingKV.md:26`): "instructions appearing at the top, tool definitions coming
  next, and then transcript entries follow at the end. Each cached value in the sequence depends on every
  token that precedes it."
- **Blast radius** (`:32`): "A change to the instructions … invalidates the cache for **the tool
  definitions and the entire transcript**. A change **deep in the transcript**, by contrast, only
  invalidates the values that follow it."
- **Ordering rule for `DynamicInstructions`** (`:74`, `:97–98`): "Place instructions and tools that remain
  **constant at the top** … group **conditional content at the bottom**." NOTE: "Placing the conditional
  content **before** the static instructions and tools invalidates the cached values and leads to
  unnecessary recomputation."
- **Profile switching is a full reset** (`:100`): "**Switching from one profile to another typically
  changes the entire prefix — which invalidates the cache for the full transcript — so treat it as a
  deliberate reset.** Design your dynamic profiles so transitions … occur at **natural boundaries in the
  conversation rather than on every turn**."
- **Stateless > stateful transforms** (`:104–106`): "A **stateless** transform that **drops** entries, like
  truncating to recent history, **invalidates parts of the cache** for the entries it removes. However, a
  transform that **replaces content in-place**, like removing debug metadata, **can preserve cache
  consistency** because the model sees the same token sequence each time."
- **Batch your trimming** (`:141`): "**Defer removing entries from the transcript until the context window
  is nearly full, then consolidate the context in a single operation rather than trimming incrementally
  after each turn.** Frequent small edits to the middle of the transcript force repeated cache
  invalidations."
- **Cheapest trim** (`:143`): "removing only the **most recent** entries is cheaper than modifying earlier
  ones."
- **Overflow error** (`:145`): the framework throws `LanguageModelError.contextSizeExceeded(_:)`; recover by
  summarizing and updating `transcript` "by accessing the history from `@SessionProperty`."
- **Restore path** (`:151–165`): `init(model:tools:transcript:)` or `init(profile:history:)`; "The session
  starts **without a KV cache**, so the model **reprocesses the full transcript** on the first call"; call
  `prewarm()` 1–2 s ahead.
- **Cache-hit-rate formula** (`:171`): "**divide the cached input tokens by the total input tokens**."

Measured third-party numbers for a two-local-model switch (**not Apple's**, and for a custom provider):
> **`.../dynamic-profiles-local-models.md:56–68`** — "**Switching models re-prefills the shared transcript
> on the newly active engine.** … Measured (0.6B↔4B): switch-in first-delta **2.35 s** … switch-back
> **0.94 s**. Append-only KV reuse only helps across consecutive *same-model* turns." Plus: "**Two
> resident models cost two footprints** … **~920 MB `phys_footprint` after the turns run**."

## 1.14 Accuracy: how history rewriting confuses the model

> **242:178** — "In addition to performance implications, the other thing you have to be careful about when
> rewriting history is **accuracy**, because **it's possible to confuse the model**."

The worked example (242:179–184), verbatim:
> "Let's say I have a session where I asked the model to **think of fun origami project names**. And then
> let's say I **add a generate title tool to the session**, and prompt it for more ideas. What do you
> expect will happen next? If we're lucky, the model will use the tool like we want. But **it's also
> possible that the model will notice it previously generated titles without the tool, and may think it's
> supposed to do that again. That's not what we want. Our history modification confused the model.**"

The doc mirror states the underlying principle more sharply:
> **[VERBATIM — `.../OptimizingKV.md:62`]** — "Modifying the transcript impacts model accuracy because
> **there's no reliable way for the model to distinguish between information that never existed and
> information that did exist but was removed from the context**. A model treats whatever's in the context
> as the complete picture and **reasons confidently from incomplete evidence**."

And three concrete tool-mutation hazards (`OptimizingKV.md:64–68`):
1. "**define the tools you need up front and keep that set unchanged**" when using `DynamicInstructions`.
2. "**Removing a tool the model previously used can cause the model to produce unexpected results** because
   it sees references in the transcript for a tool that no longer exists… **If you do remove any tools,
   also remove any associated output that refers to them.**"
3. "**Adding a new tool late in a conversation can produce unexpected behavior.** The model follows patterns
   established in earlier turns and might not incorporate a newly available tool into its responses." ←
   this is literally 242:182 in prose form.

> **242:185–187** — "When you start to get into **nuanced transcript modifications** like this, it becomes
> **even more important to use the Evaluations framework to create eval sets and quantify the effect of
> context engineering strategies**. **Data driven optimization is the only way to be confident.** I highly
> recommend watching all of our videos about the evaluations framework."

## 1.15 242 wrap-up

> **242:190–192** — "We've shown you how dynamic profiles allow you to **steer model behavior** and
> **manage your session's transcript**. We talked through patterns like **phone-a-friend and baton-pass**,
> **tool calling mode**, **manual transcript management**, and even **KV caches**."

> **242:192–193** — "**try playing around with the sample app**. Or **test out PCC together with the
> revamped Xcode instrument**."

---

# PART 2 — WWDC26 243: Debugging & profiling FM features with Instruments

Presenter: Erik, "an **AI Tools Engineer**" (243:1).

## 2.1 Why FM features are hard to debug

> **243:5–10** — "The features that create the best experiences **aren't static. They adapt based on
> context.** … `DynamicInstructions` lets you specify exactly which instructions and tools the model can
> access. It **re-evaluates before every request** … **That flexibility is what makes these features so
> responsive, and also what makes them harder to debug.**"

> **243:11–14** — "Building with … LLMs is different from traditional development. **Traditional code is
> predictable. LLMs are non-deterministic — the same input can produce different outputs.** When a feature
> **loses context or responds too slowly**, tracking down the cause isn't straightforward."

> **243:19** — Prerequisite sessions: "**'What's new in the Foundation Models framework'** and **'Build
> agentic app experiences with the Foundation Models framework'**." *(= 241 and 242.)*

### The three challenges (243:20–34)

| # | Challenge | Verbatim |
|---|---|---|
| 1 | **Probabilistic output** | 243:21–26 "Give a traditional function the same input twice, and you get the same output. LLMs don't work that way… **which means standard unit testing breaks down. You can't assert that an output matches a hardcoded string. You have to evaluate the quality and intent of the response instead.**" |
| 2 | **Model-to-model communication** | 243:27–30 "Powerful features often rely on **multiple models working together**… **Getting data to flow reliably between those models, and recovering gracefully when something goes wrong, is where real complexity lives.**" |
| 3 | **Observability** | 243:31–33 "When something breaks in a multi-model pipeline, **it can be very hard to know where it went wrong. You need visibility into each step: what the model received, what it decided, and why.**" |

Example given for #2 (243:29): "in a recipe app, one model might **identify ingredients in a photo**, while
a second **generates a recipe from that result**."

### The mental model the Instrument is built around

> **243:35** — "At its core, an LLM application does three things: **a person sends a prompt, the model
> reasons about it, and the person gets a response.**"

> **243:40** — "**The loop works like this: the person sends a prompt, the model reasons about it and calls
> a tool, that tool performs an action, the model takes the result and generates a final response, which
> can kick off the loop again.**"

> **243:41–43** — "**Each extra step adds latency. Each step is a new place for failure. Understanding this
> loop is the basis for everything the Foundation Models Instrument shows you.**"

## 2.2 The feature under test

> **243:45–51** — "a **crafting companion app** where you can **keep a journal of your craft projects**. The
> app lets you **record craft progress, ask questions about specific crafts, and generate tutorials**.
> Recently, I had an idea for an **interactive brainstorming feature**… **This feature uses two sets of
> instructions**: one for **brainstorming ideas**, and a second for **tutorial generation**. The
> brainstorming instructions include **two tools: a `GenerateCraftIdeaTool` and a
> `SwitchToTutorialModeTool`**. **Both sets of instructions use the server model on Private Cloud Compute**,
> one for quick idea generation and the other to generate more detailed tutorials."

**Named symbols from 243 (as spoken/on-screen):**
- `GenerateCraftIdeaTool` (243:50) — also rendered "`GenerateCraftIdeasTool`" at 243:106 and
  "`generateCraftIdea`" at 243:121. **Caption inconsistency; exact name UNVERIFIED.**
- `SwitchToTutorialModeTool` (243:50) / tool name `switchToTutorialMode` (243:98, 243:121, 243:125)
- `BrainstormDynamicInstructions` (243:105) — the `DynamicInstructions` type that had the bug.

## 2.3 The profiling workflow (exact click path)

> **243:53–59** — "The project is already open in Xcode. To begin profiling, I'll **open the Product menu
> and select Profile**. **Xcode will build the app locally.** From the **template chooser**, I'll select
> the **Foundation Models template** and click **Record**."

**The privacy dialog — a real gotcha (243:57–59), verbatim:**
> "**This instrument captures prompt and response data from your device, which can include sensitive
> information. Logging is off in production but it's on for the duration of your trace so keep your trace
> files somewhere safe. Select 'Record Anyway' to get started.**"

⇒ Three facts: (a) prompt/response **text** is captured into the `.trace`; (b) **logging is off in
production**, on only for the trace's duration; (c) `.trace` files are sensitive artifacts — do not commit
them, do not attach to public bug reports without scrubbing.

**Requirements (243:146–148), verbatim:**
> "To get started with the improved Foundation Models Instrument, **install Xcode 27**. Then, on the device
> you'd like to run and profile your app on, **update to the latest OS releases**. **Its important to note
> that this Instrument supports using any model you use with the Foundation Models framework.**"

⇒ The Instrument is **model-agnostic**: on-device `SystemLanguageModel`, `PrivateCloudComputeLanguageModel`,
**and** third-party `LanguageModel` providers (e.g. MLX-backed) all show up.

## 2.4 Instruments UI anatomy

> **243:68–73** — "**The top section holds the tracks.** **Tracks show activity on the timeline, and each
> track can contain multiple lanes with charts that show levels or regions.** Below the timeline is **the
> detail view. It shows summary information about the range you're currently inspecting.** If you **click
> a bar in the timeline or a row in the detail view**, **the inspector opens up on the right** giving you
> a closer look at what you've selected."

> **243:74–77** — "**The Foundation Models Instrument has 6 lanes in the timeline.** These give you a quick
> overview of **session structure and latencies**. Alongside the timeline, there's a **tree detail view**.
> **That's where you can really dig into the model's chain of thought.**"

### ⚠️ Only 2 of the 6 lanes are named in the transcript

| Lane | Named? | What it shows (verbatim) |
|---|---|---|
| **Instructions** | ✅ 243:78 | "**The Instructions lane shows how long a given set of instructions and tools was active. One set can cover multiple requests.**" |
| **Model Inference** | ✅ 243:81–83 | "**The Model Inference lane has two types of bars: yellow and orange.** **Yellow bars represent how long the system spent processing the input prompt.** **Orange bars represent how long it took to generate the response.**" |
| lanes 3–6 | ❌ **not named** | Unknown. Likely candidates given the tree hierarchy: Sessions, Requests, Tool Calls, Asset/Model Load. **UNVERIFIED — do not assert in a guide.** |

**Colour legend (memorize this, it's the fastest read in the whole trace):**
- 🟨 **Yellow = prefill** (input prompt processing) → shrink by shortening the prompt / preserving KV cache.
- 🟧 **Orange = decode** (response generation) → shrink by generating fewer tokens / streaming.

**Diagnostic use of the Instructions lane (243:80), verbatim:**
> "Looking at this lane, it's clear **only one set of instructions was active for the entire session** but
> the feature was supposed to use two, **so something went wrong during the handoff**."

⇒ **The Instructions lane is the profile-switch visualizer.** One contiguous region per resolved
instruction set. If your `DynamicProfile` is supposed to switch and the lane shows a single unbroken
region, the switch never happened.

After the fix (243:117–119):
> "**The Instructions lane now shows two distinct instructions active during this experience.** The first is
> a **brainstorming** instruction and the second is a **tutorial generation** instruction. That lines up
> exactly with the brainstorm experience design we covered earlier."

## 2.5 The tree detail view — the model's chain of thought

> **243:84–85** — "**The timeline gives you a quick overview but the real power is in the tree view.** It
> takes everything logged during this recording and **organizes it into a hierarchy: sessions, requests,
> model inferences, instructions, prompts, and responses.**"

**The hierarchy, as stated (243:85):**
```
Session
└── Request                       ("Session 1 had two requests" — 243:87)
    └── Model Inference           (multiple per request — 243:89, 243:124)
        ├── Instructions          (243:96)
        ├── Prompt                (243:95)
        └── Response  |  Error    (243:90)
        └── Tool Call(s)          ("a few tool calls" — 243:89)
```

**The invariant to check first (243:90), verbatim:**
> "**Every model inference should have instructions, a prompt, and either a response or an error.**"

> **243:87–89** — "**Session 1 had two requests.** The first one was kicked off by the prompt starting with
> **'Please generate 3 craft ideas.'** That request was made up of **two model inferences and a few tool
> calls**."

⇒ **One user "request" ≠ one model inference.** A single `respond(to:)` fans out into N inferences (one per
tool-calling loop iteration). This is the structural fact that makes the tree view necessary.

> **243:91** — "**Click any node in the tree to pull it up in the inspector.**"

### The model-inference inspector

> **243:92–94** — "**The model inference detail shows a summary of the instructions, prompt, and response
> that made up this call.** **Scroll down and you'll find duration visualizations and token usage
> metrics.**"

> **243:130** — "**The metrics and duration sections break down token usage for this inference.** These
> numbers are your starting point for understanding and improving the efficiency of an experience."

⇒ Inspector sections for a **Model Inference** node: **summary (instructions / prompt / response)**,
**duration visualizations**, **metrics (token usage)**.

### The instructions inspector

> **243:96–97** — "Let's select the **Instructions node** to see how they're set up. **The inspector shows
> that this instruction only had one tool associated with it.**"

⇒ The Instructions node inspector **enumerates the tools bound to that instruction set** — the single most
useful thing in the Instrument for debugging `DynamicInstructions`.

### The Info column

> **243:127** — "**The info column is a great way to quickly flag nodes worth a closer look: things like
> errors, long durations, and large token counts.**"

⇒ Three flag categories: **errors**, **long durations**, **large token counts**. Use it as a triage filter.

## 2.6 The worked bug: a silent failure

**Symptom (243:63–66):**
> "Hm. That's not right. **The model was supposed to kick off a tutorial but instead it just offered more
> ideas.** Something's off."

Demo detail: the initial suggestions were **Yarn PomPom, Fabric Pouch, Paper Butterfly** (243:61); the
presenter picked Paper Butterfly.

**Diagnosis chain:**
1. **Instructions lane** shows one unbroken region ⇒ the handoff never happened (243:80).
2. Model-inference inspector shows the prompt tied to those instructions (243:95).
3. **Instructions node** inspector: "**only had one tool associated with it**" (243:97).
4. **243:98 (the money quote):** "**The prompt references the `switchToTutorialMode` tool but that tool
   isn't actually configured with this instruction.**"
5. **243:99:** "**Without it, the app has no way to switch from brainstorm mode to tutorial mode, so the
   crafter gets stuck in a loop.**"

**Why this class of bug is nasty (243:100–103), verbatim:**
> "Looking at the subsequent nodes in the tree, **this was a silent failure. The model kept accepting input
> and making tool calls but never threw an error. There was no clear signal that anything had gone wrong.
> That makes it a hard bug to catch.**"

**The fix (243:105–106), verbatim:**
> "I'll look at the **`BrainstormDynamicInstructions`** definition. **In the `Instructions` block, the
> `SwitchToTutorialMode` tool is mentioned in the prompt but only the `GenerateCraftIdeasTool` is listed in
> the toolset, so let's add it.**"

**[RECONSTRUCTED — 243:105–106]** — before/after:
```swift
// BEFORE (buggy)
struct BrainstormDynamicInstructions: DynamicInstructions {
    var body: some DynamicInstructions {
        Instructions {
            "Help the person brainstorm craft ideas."
            "When they choose one, call switchToTutorialMode."   // ← mentioned in text…
        }
        GenerateCraftIdeasTool()                                  // ← …but not in the toolset
    }
}

// AFTER (fixed)
struct BrainstormDynamicInstructions: DynamicInstructions {
    var body: some DynamicInstructions {
        Instructions {
            "Help the person brainstorm craft ideas."
            "When they choose one, call switchToTutorialMode."
        }
        GenerateCraftIdeasTool()
        SwitchToTutorialModeTool()                                // ← added
    }
}
```

**Generalized lesson for a guide:** *instructions prose and the declared toolset can silently drift apart.*
The `Instructions` block is text; the tool list is code; nothing cross-checks them. The Instructions node
inspector is the only place that shows both side by side.

**Verification after the fix (243:117–126):**
- Instructions lane: two distinct regions (243:117).
- 243:121–123: "**The first set of instructions now includes both the `generateCraftIdea` and
  `switchToTutorialMode` tools. That confirms the model had everything it needed to make the switch. The
  fix worked.**"
- 243:124–126: "**The instruction change happened after the second model inference of Request 2.** That
  inference resulted in a **tool call to `switchToTutorialMode`, passing the selected craft as an
  argument**. And **in the following request, the instructions correctly switched over to the tutorial
  generator, with the selected craft passed along as context.**"

⇒ **Timing fact worth capturing:** the profile/instruction switch takes effect **on the *next* request**,
not mid-request. The tool call happened in Request 2's 2nd inference; the new instructions appear in
Request 3. This is consistent with 242:59 ("the body … is re-evaluated **each time the model is
prompted**").

## 2.7 The three performance metrics

> **243:128** — "**Request 1's first model inference took a bit longer than I was expecting**, so let's take
> a look."

> **243:131** — "**You can measure performance using three key metrics.**"

| Metric | Definition (verbatim) | Symptom (verbatim) | Fix (verbatim) |
|---|---|---|---|
| **Time to First Token** | 243:132 "measures **how long it takes for the model to begin generating a response after receiving a prompt**" | 243:133 "**A high Time to First Token means people are staring at a blank screen.**" | 243:134 "**To reduce it, shorten your prompt.**" |
| **Tokens per Second** | 243:135 "measures **overall generation speed of the response**" | — | 243:136 "**Use it to benchmark performance across different prompt configurations and catch regressions after changes.**" |
| **Total Latency** | 243:137 "**the complete time from sending the request to receiving the final response**" | 243:138 "**This is the number people feel most directly.**" | 243:139 "**To reduce perceived Total Latency, utilize streaming to surface partial results sooner.**" |

Note the precise wording on Total Latency: streaming reduces **perceived** latency, not actual.

> **243:140–142** — "**Running a trace is where optimization starts. These metrics tell you exactly where
> time and resources are going and point you toward the right fix. Use the model inference node to get a
> clear picture of your token usage.**"

### Metrics 243 does NOT name but the docs do

`RuntimePerformance.md` (the written companion, `.../AppleFoundationModels/RuntimePerformance.md`) adds:
- **Cache hit rate** (`:27`) — "percentage of input tokens served from the KV prefix cache (**divide cached
  input tokens by total input tokens**)"
- **Input tokens** (`:28`) — "tokens from **instructions, tools, schemas, and prompts**"
- **Output tokens** (`:29`)
- **Reasoning tokens (PCC only)** (`:30`) — "tokens used for **intermediate reasoning in reasoning mode**"
- **Asset load times** (`OptimizingKV.md:171`)
- Tool-call **execution duration and output** (`RuntimePerformance.md:55`)
- `LanguageModelSession.usage` (`RuntimePerformance.md:80`) — "programmatic token usage tracking (Beta)",
  type `LanguageModelSession.Usage` (`Overview.md:187`)

⇒ **The cache-hit-rate read is the connective tissue between 242 and 243.** 242:176–177 says "check the
debugging video for detecting cache invalidations," but 243 never actually says the words "cache hit
rate" — the doc does. Flag this in the guide.

## 2.8 243 wrap-up + next steps

> **243:143–145** — "Once you've ironed out the bugs, **the next thing to explore is evaluation. Watch
> 'Meet the Evaluations framework'** to see how you can **measure and improve the quality of your prompts
> by using structured evaluation**."

> **243:151** — "**When something isn't working as expected, the Foundation Models Instrument is there to
> help you debug, giving you direct visibility into framework behavior right in context.**"

---

# PART 3 — Cross-check: transcripts vs local docs

## 3.1 Agreements

| Claim | 242/243 | Local doc |
|---|---|---|
| Body re-evaluates before every request | 242:59, 243:8–9 | `DynamicSessions.md:15`, `OptimizingKV.md:72` |
| Append preserves KV cache; rewrites invalidate | 242:170–171 | `OptimizingKV.md:28`, `:32` |
| Profile switch = full prefix change | (implied by 242:171) | `OptimizingKV.md:100` — explicit, stronger |
| `historyTransform` is non-mutating/local | 242:78–79 | `OptimizingKV.md:104` "don't modify the global transcript" |
| `history` property is stateful/lossy | 242:102 | `OptimizingKV.md:119` "modifies the transcript between turns" |
| Tool add/remove mid-session confuses the model | 242:180–184 | `OptimizingKV.md:64–68` — three named hazards |
| Instrument shows token usage + durations | 243:93, 243:130 | `RuntimePerformance.md:9`, `:70–76` |
| Instrument requires Product > Profile → FM template → Record | 243:53–56 | `RuntimePerformance.md:16–20`, `ManagingContextWindow.md:24–28` |
| Use Evaluations to quantify context-engineering changes | 242:185–187, 243:144–145 | `UsingPrivateCloudCompute.md:27` ("evaluate it with the Evaluations framework") |
| PCC = deeper reasoning, larger context | 242:45, 242:51–54 | `UsingPrivateCloudCompute.md:18`, `:29–35` |

## 3.2 Discrepancies / drift to flag in a guide

| # | Issue | Detail |
|---|---|---|
| **D1** | **Protocol spelling** | Transcripts + prose docs: `DynamicProfile`. Compiled Swift + Apple doc URL: **`LanguageModelSession.DynamicProfile`**. (`StructuredToolOutputSessionTests.swift:48`; `OptimizingKV.md:104` URL path `languagemodelsession/dynamicprofile/historytransform(_:)`) |
| **D2** | **Tool-mode type name** | `Overview.md:127` links `/documentation/foundationmodels/**toolcallmode**`; compiled code uses **`GenerationOptions.ToolCallingMode`** with a `.kind`. Prefer the compiled name. |
| **D3** | **Macro spelling** | `DynamicSessions.md:131` says "`@SessionPropertyEntry()` macro"; compiled code writes **`@SessionPropertyEntry`** with no parens. |
| **D4** | **Availability** | `DynamicSessions.md:7` claims "Beta (**iOS 26.0+**…)". Everything else — `Origami.md:7` ("**iOS 27.0+**… Xcode 27.0+"), all compiled code (`@available(iOS 27.0, macOS 27.0, visionOS 27.0, *)`), and 243:146 ("install **Xcode 27**") — says **27**. **Treat `DynamicSessions.md:7` as wrong.** |
| **D5** | **Craft app modes** | 242 = brainstorming / planning / reviewing. `Origami.md` sample = `.brainstorm` / `.tutorial` / `.term`. 243 = brainstorm / tutorial only. Three inconsistent tellings of the same demo. |
| **D6** | **Model chosen per mode** | 242:45 puts **brainstorm on PCC** with temperature 1. `Origami.md:46` puts **brainstorm on-device** at 1.0 and tutorial on PCC. 243:51 puts **both** on PCC. Don't present any of these as "the" recommended mapping. |
| **D7** | **`reasoningLevel` placement** | 242:52 calls it a profile-level thing (`.reasoningLevel(.deep)`). `UsingPrivateCloudCompute.md:124–131` sets it per-call via `contextOptions: ContextOptions(reasoningLevel: .deep)`. `Origami.md:158–160` shows **both** on one profile (`.reasoningLevel(.deep)` AND `.contextOptions(ContextOptions(reasoningLevel: .deep))`) — that looks like doc-sample sloppiness. Levels are `.light`, `.moderate`, `.deep` (`UsingPrivateCloudCompute.md:122`). |
| **D8** | **Cache-hit-rate metric** | 242:177 points at 243 "for detecting cache invalidations with Instruments," but **243 never names a cache metric**. The metric (`cached input tokens ÷ total input tokens`) only appears in `OptimizingKV.md:171` / `RuntimePerformance.md:27`. |
| **D9** | **Body evaluation count** | 242:59 "**each time** the model is prompted" (implies once). Third-party measurement: **7 evaluations for 3 turns** (`dynamic-profiles-local-models.md:48`). Guides must say "**at least once, possibly several times — keep `body` pure**." |
| **D10** | **Release year** | `transcripts/wwdc2026-241.txt:3` says "**Our 2027 release**…" while the OS versions are 27 and the conference is WWDC26. Note the naming, don't editorialize. |

## 3.3 API surface consolidated (everything I can name with a source)

**Types / protocols**
- `LanguageModelSession.DynamicProfile` (protocol) — `StructuredToolOutputSessionTests.swift:48`
- `Profile` (struct, result-builder-constructible) — 242:32; `StructuredToolOutputSessionTests.swift:56`
- `Profile(model:){ }` initializer — `Origami.md:70`; `dynamic-profiles-local-models.md` uses `.model(_:)` modifier instead
- `DynamicInstructions` (protocol, has `var body: some DynamicInstructions`) — 242:39; `OptimizingKV.md:77–80`
- `DynamicProfileModifier` (protocol) — **242:83 only**; shape UNVERIFIED
- `SessionPropertyValues` (extension point) — `StructuredToolOutputSessionTests.swift:15`
- `@SessionPropertyEntry` (macro, attached to a `var` with an initial value) — `:16`; 242:106–107
- `@SessionProperty(\.keyPath)` (property wrapper) — `:51`; `DynamicSessions.md:118`
- `LanguageModelSession.properties` — `StructuredToolOutputSessionTests.swift:120`
- `GenerationOptions.ToolCallingMode` + `.kind` (`.allowed` / `.required` / `.disallowed`, non-frozen) — `ToolCallingModeResolution.swift:15–41`
- `Transcript.ToolDefinition`, `Transcript.ToolOutput`, `Transcript.StructuredSegment` — `ToolCallingModeResolution.swift:35`, `StructuredToolOutputSessionTests.swift:122–133`
- `Transcript.Entry` — `DynamicSessions.md:119`
- `PrivateCloudComputeLanguageModel` — 242:45; `UsingPrivateCloudCompute.md:43`
- `ContextOptions(reasoningLevel:)` with `.light/.moderate/.deep` — `UsingPrivateCloudCompute.md:122–131`
- `LanguageModelError.contextSizeExceeded(_:)` — `OptimizingKV.md:145`
- `LanguageModelSession.ToolCallError` (has `.tool`, `.underlyingError`) — `ToolCalling.md:122–139`
- `LanguageModelSession.Usage` — `Overview.md:187`

**Profile modifiers** (union of 242 + `dynamic-profiles-local-models.md:40–44` + compiled code)
`.model(_:)` · `.temperature(_:)` · `.samplingMode(_:)` · `.maximumResponseTokens(_:)` ·
`.reasoningLevel(_:)` · `.toolCallingMode(_:)` · `.historyTransform(_:)` ·
`.transcriptErrorHandlingPolicy(_:)` · `.contextOptions(_:)` · `.modifier(_:)` ·
lifecycle: `.onActivate` `.onDeactivate` `.onPrompt` `.onResponse` `.onToolCall` `.onToolOutput`

**Session members touched**
- `LanguageModelSession(profile:)` — 242:58; `DynamicSessions.md:81`
- `LanguageModelSession(profile:history:)` — `OptimizingKV.md:38`
- `LanguageModelSession(model:tools:transcript:)` / `init(transcript:)` — `OptimizingKV.md:151`, `:158`
- `session.transcript` — **now mutable** (242:165)
- `session.isResponding` — gate for mutation (242:166–167)
- `session.transcriptErrorHandlingPolicy` — 242:159 (spoken as "set it directly on your session")
- `session.prewarm()` / `prewarm(promptPrefix:)` — `OptimizingKV.md:40`, `:164`
- `session.properties.<name>` — `StructuredToolOutputSessionTests.swift:120`

**Modifier precedence (from the doc mirror only, `DynamicSessions.md:84–90`):**
1. Call-site arguments (e.g. `options:` on `respond()`)
2. Innermost dynamic profile or profile modifier
3. Dynamic profile modifiers on the outer container

---

# Source inventory (everything I actually read this session)

**Read in full (Read tool):**
1. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-242.txt` (195 lines) — PRIMARY
2. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-243.txt` (154 lines) — PRIMARY
3. `/Volumes/ExtStor/FM and MLX and CoreAI/repos/noemaai-labs__noema-ios/DocumentationforAPIs&SDKs/AppleFoundationModels/DynamicSessions.md` (173 lines)
4. `.../AppleFoundationModels/OptimizingKV.md` (186 lines)
5. `.../AppleFoundationModels/Origami.md` (214 lines)
6. `.../AppleFoundationModels/RuntimePerformance.md` (88 lines)
7. `.../AppleFoundationModels/ManagingContextWindow.md` (100 lines)
8. `.../AppleFoundationModels/ToolCalling.md` (187 lines)
9. `.../AppleFoundationModels/Overview.md` (189 lines)
10. `.../AppleFoundationModels/UsingPrivateCloudCompute.md` (145 lines)
11. `/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/dynamic-profiles-local-models.md` (133 lines)
12. `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-swift-lm/Libraries/MLXFoundationModels/ToolCalling/ToolCallingModeResolution.swift` (50 lines)
13. `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-swift-lm/IntegrationTesting/IntegrationTestingTests/MLXFoundationModelsIntegration/ToolCalling/StructuredToolOutputSessionTests.swift` (144 lines)

**Read in part (Bash `sed`/`grep`):**
14. `/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/agentic-security-checklist.md` (lines 1–193)
15. `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-and-ai-foundation-models.txt` (lines 40–300)
16. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-241.txt` (grep only — lines 3, 5, 10, 68–69, 79–83, 96–102, 128–139)
17. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-232.txt`, `-246.txt`, `-339.txt` (first 5 lines each, for session identification only)

**Confirmed absent:** `/Volumes/ExtStor/FM and MLX and CoreAI/docs/` contains only 6 files, **none about
Foundation Models** (they are Core AI, MLX, and Speech docs). The FM doc mirror lives under
`repos/noemaai-labs__noema-ios/DocumentationforAPIs&SDKs/AppleFoundationModels/`. `notes/` was empty at
session start.

**External URLs referenced but NOT fetched this session** (cited by the local files; treat as pointers):
- `https://github.com/apple/foundation-models-utilities`
- `https://developer.apple.com/documentation/foundationmodels/composing-dynamic-sessions-with-instructions-and-profiles`
- `https://developer.apple.com/documentation/foundationmodels/optimizing-key-value-caching-in-language-model-sessions`
- `https://developer.apple.com/documentation/foundationmodels/analyzing-the-runtime-performance-of-your-foundation-models-app`
- `https://developer.apple.com/documentation/foundationmodels/origami-crafting-a-dynamic-tutorial-for-apple-intelligence`

---

# Open questions / UNVERIFIED

1. **The other 4 Instruments lanes.** 243:74 says 6; only *Instructions* and *Model Inference* are named.
   Need a screenshot or the written doc to enumerate the rest. **Do not guess in a guide.**
2. **`historyTransform` exact signature.** Is it `([Transcript.Entry]) -> [Transcript.Entry]`? `async`?
   `throws`? `@Sendable`? Is the parameter a distinct `History` type rather than an array? (`OptimizingKV.md`
   passes it to a helper `clearDebugFromHistory(history)` with no type annotation.)
3. **`DynamicProfileModifier` requirements.** 242:83 names the protocol only. Assumed SwiftUI-shaped
   `func body(content: Content) -> some LanguageModelSession.DynamicProfile`. Unconfirmed.
4. **`onToolCall` arity/overloads.** Compiled code shows `{ }` (no args); WWDC26 347 sketch shows
   `{ call in … }` with `call.toolName`. Are both real? Is the closure `async throws`? Does throwing from
   `onToolCall` really block the tool (347 claim, not in 242/243)?
5. **`transcriptErrorHandlingPolicy` on a session** — settable property, or init parameter? 242:159 only
   says "you can set it directly on your session." Also: what is the enum's full type name?
   (`TranscriptErrorHandlingPolicy`? nested under `LanguageModelSession`?)
6. **`Profile(model:){ }` vs `.model(_:)`.** Both spellings appear in different sources. Are both real, or
   is one a doc error?
7. **Does `.temperature(1)` take `Double`?** 242:47 says "set the temperature to 1"; `Origami.md` writes
   `1.0` and `DynamicSessions.md` writes `1.0`/`0.2`. Almost certainly `Double`, but the literal `1` in the
   narration is ambiguous.
8. **`samplingMode` modifier** — named at 242:33 as a thing a Profile modifier configures, and listed in
   `dynamic-profiles-local-models.md:40`. No example anywhere. What are its cases?
9. **`Skills` type in FM utilities** — 242:137 names it; the forums name a `SkillActivation` module
   (thread 835165) that reportedly **fails to build**. Are `Skills` and `SkillActivation` the same thing?
   What is the API?
10. **Whether the Instruments trace records PCC-side reasoning tokens as a separate lane/metric.**
    `RuntimePerformance.md:30` names "reasoning tokens (PCC only)" as a metric; 243 doesn't mention it.
11. **Baton-pass with a `.required` tool-calling mode** — 242 presents these separately. Is the combination
    the recommended agentic architecture ("agentic systems that represent all actions as tool calls",
    242:146)? Not stated.
12. **The `history` window's exact type.** 242:72 calls it "a window into the transcript." Is
    `@SessionProperty(\.history)` typed `[Transcript.Entry]` (per `DynamicSessions.md:119`) or a dedicated
    `History` struct? `history.suffix(50)` in `OptimizingKV.md:132` implies a `Collection`.
13. **Does the Instruments Foundation Models template work against the Simulator**, or device-only? 243:147
    says "on the device you'd like to run and profile your app on, update to the latest OS releases" —
    implies device, doesn't forbid Simulator.
14. **Session/Request numbering semantics** in the tree ("Session 1", "Request 2") — is a "Session" one
    `LanguageModelSession` instance, and does it survive profile switches? (242's whole point is that one
    session hosts many profiles, and 243:117 shows two instruction regions inside one recording — but 243
    never says whether that was one Session node or two.)
