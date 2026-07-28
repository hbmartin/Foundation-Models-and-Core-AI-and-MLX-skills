# Corpus gaps the lead agent found and filled

Two things the original research plan missed, discovered by reading the forum captures directly.

---

## A. `apple/foundation-models-utilities` — was NOT in the clone list, now cloned

**Found via:** Apple Developer Forums thread 835165 ("SkillActivation Framework Fails to Build in
Xcode 26 When Using foundation-models-utilities") which cites the repo URL.
**Repo:** https://github.com/apple/foundation-models-utilities — **459 stars**, last push
2026-07-16. Cloned to `repos/apple__foundation-models-utilities`.

This is the package that sessions 241 and 242 kept promising ("updated between OS releases…
emerging and experimental building blocks"). It is small, readable, and **documents mechanisms that
appear in NO transcript and NO Apple doc page we have.** It should anchor at least two guides.

### Package facts
- Product: `FoundationModelsUtilities`; SPM `from: "1.0.0"`.
- **"Supported platforms: Apple platforms and select Linux distributions like Ubuntu."**
  ← concrete confirmation of the "Foundation Models everywhere Swift runs" claim in session 241.
- Issue reporting goes to the **Apple Developer Forums**, not GitHub issues.
- Ships **two agent skills**: `skills/foundation-models-utilities/SKILL.md` and — notably —
  **`skills/foundation-models-language-model-protocol/SKILL.md`**. The second is Apple's own
  written guidance on implementing the `LanguageModel` protocol. Primary source for that guide.
- Source layout is the feature list: `LanguageModels/ChatCompletionsLanguageModel.swift`;
  `History/{DropCompletedToolCalls, RollingWindow, SummarizeHistory, TranscriptRendering}.swift`;
  `Skills/{Skill, SkillActivations, SkillBuilder, Skills}.swift`; plus a `Documentation.docc`.
  Tests are split `SkillsTests` / `LanguageModelTests` / `HistoryTests`, and there is a separate
  `FoundationModelsUtilitiesIntegrationTests` target.

### `ChatCompletionsLanguageModel`
```swift
let model = ChatCompletionsLanguageModel(
  name: "minimax-m2.5",
  url: URL(string: "http://localhost/v1:8000")!,
  supportsGuidedGeneration: false   // some local servers don't support it
)
let session = LanguageModelSession(model: model)
```
→ **capability declaration is a real, user-visible part of the `LanguageModel` protocol**, not just
an internal detail. This is the bridge to "the large ecosystem of open source utilities built
around the chat completions protocol" — i.e. **mlx_lm.server, Ollama, LM Studio, vLLM all become
Foundation Models backends.** That closes the loop with session 232 and is a *big* deal for the
guide series: `mlx_lm.server` + `ChatCompletionsLanguageModel` = any HF model behind
`LanguageModelSession`, today, without waiting for `MLXLanguageModel`.

⚠️ Known defect (forum 838444): `buildURLRequest` decides versioning with
`baseURL.pathComponents.contains("v1")` and appends `/chat/completions` or `/v1/chat/completions`.
Hardcoding `v1` breaks servers on other version paths. Worth documenting as a live limitation.

### History management modifiers — the concrete answer to "context management"
Three modifiers, **applied outside-in**:
```swift
struct MyProfile: LanguageModelSession.DynamicProfile {
  let status: Status
  var body: some DynamicProfile {
    Profile {
      Instructions("A conversation between a user and a helpful assistant.")
      ToggleDarkModeTool()
    }
    .summarizeHistory(entryThreshold: 10, model: status.summarizerModel)
    .rollingWindow(entries: 10)
    .droppingCompletedToolCalls()
  }
}
```
Reading order per the README: drop completed tool calls → rolling window → summarize (and
summarization "runs only if the rolling window of 10 entries exceeds 5000 tokens").
**Apple explicitly says "There's no one-size-fits-all solution, so we encourage composing
strategies together."**

⚠️ **Naming correction to my orientation notes:** the protocol is nested —
**`LanguageModelSession.DynamicProfile`**, not a top-level `DynamicProfile`. The `body` returns
`some DynamicProfile`. Guides must get this right.

### `Skills` — procedural knowledge loading, and it is KV-cache-aware by design
`Skills` conforms to **`DynamicInstructions`**, is built with a **result builder**, and takes a
**`SkillActivations`** instance that tracks which skills are live. `SkillActivations` conforms to
**`Observable` and `RandomAccessCollection`**, so it can drive SwiftUI directly. Purpose, verbatim:
*"adding extra directions about performing specific tasks into a `LanguageModelSession` transcript
on a **just-in-time** basis. This prevents **context pollution** and helps optimize
**time-to-first-token**."*

**The central design distinction — this is the best single teaching example of KV-cache economics
in the whole corpus.** A `Skill` is initialized with *either* `prompt:` (or a trailing
`@PromptBuilder`) *or* `instructions:`, and the choice changes where content lands:

| Init with | Content goes | KV cache | Model priority |
|---|---|---|---|
| `prompt:` | into a **tool output** entry matching the activation tool call (appended) | **preserved** | normal |
| `instructions:` | appended **into the first instructions entry** (rewrites history) | **invalidated** | high — "models are typically trained to obey instructions with high priority" |

In both cases **the model activates a skill by generating a tool call.**

`instructions:`-based skills can also take **`allowsDeactivation: true`**, letting the model issue
a *second* tool call to remove the skill's content from its instructions — described as
*"a powerful tool for combating context pollution, especially when combined with history
transformations that remove complete tool calls."* The README carries ASCII transcript diagrams for
before/after/after-dropping-tool-calls; those diagrams are worth reproducing in a guide.

This is the concrete, shipping realization of the abstract KV-cache warning in session 242
("appending preserves the cache; rewriting instructions invalidates it"). Pair them.

### Open question
Session 241 said **the core FoundationModels framework itself** is going open source. I searched
`apple/*` and `swiftlang/*` on GitHub and found **no** standalone repo for the core framework —
only `foundation-models-utilities`, `python-apple-fm-sdk`, `coreai-models`. So as of 2026-07-27 the
core appears to still ship only in the OS/SDK. **Flag this as unresolved rather than asserting it.**

---

## B. The Apple Developer Forums captures — the strongest signal for what guides must cover

`forums/machine-learning-and-ai-foundation-models.txt` is an **RSS feed dump** of the FM forum
topic. Items are dated **June–July 2026**, which independently corroborates the WWDC26 / iOS 27
timeline. Note the OS beta codename that appears: **"macOS Golden Gate Developer Beta 4"** = macOS 27.

### Recurring pain clusters (each is a guide section, some a whole guide)

**1. Availability & gating — the single largest cluster**
- Thread 835211: on iOS 27 beta 1, `SystemLanguageModel.default.availability` returns
  **`.appleIntelligenceNotEnabled`** unless the user enables *"Siri"/"Hey Siri"* or
  *"Press Side Button for Siri"*. Developer calls this unintuitive.
- Thread 836760: same finding on macOS since beta 2 — "Foundation models are not accessible if Siri
  AI is not enabled", with an explicit **EU availability** worry.
- Thread 836810: **no `Required Device Capabilities` equivalent for Apple Intelligence**, so an app
  whose *primary* function is FM has no way to prevent install on unsupported devices. Unanswered
  distribution-strategy problem.
- Thread 834652: watchOS 27 + PCC — if a Series 11 watch is paired to an iPhone 15 (no Apple
  Intelligence), can the watch use PCC? Is there a separate watchOS Apple Intelligence setting?

**2. Guardrails, refusals, and safety errors — with a taxonomy problem**
- Thread 836673 (excellent bug report): a shipping health app that summarizes the user's *own*
  glucose/cycle data worked on iOS 26.x, then **every prompt is refused on iOS 27 beta 2**. Crucially
  the error is **`LanguageModelError` ("The model refused to answer" / "May contain sensitive
  content"), NOT `GenerationError.guardrailViolation`.** Two distinct refusal mechanisms exist and
  developers conflate them. A guide must draw that distinction explicitly.
- Thread 836285: bare `session.respond(to: "List all states of USA.")` in `#Playground` returns
  **`com.apple.SensitiveContentAnalysisML error 15`** on Xcode 27 beta 2. Toggling Apple
  Intelligence off/on doesn't help.
- Thread 835777: guardrail behavior **changed under a shipping app** over a couple of weeks;
  reveals the real API **`SystemLanguageModel(guardrails: .permissiveContentTransformations)`** and
  the developer's own note that **`.permissiveContentTransformations` does not apply to `Generable`**.
- Thread 791250 (Apple-posted, pinned): the official feedback channel is **`#Playground` in Xcode**
  → thumbs-up icon next to the response → attach the session. Since macOS/iOS 26 Beta 4.

**3. Adapters + Background Assets — concrete, undocumented CLI**
- Thread 829108: adapter loads fine locally via `SystemLanguageModel(fileURL:)` on device, but fails
  with **`compatibleAdapterNotFound`** when delivered as an Apple-hosted managed asset pack through
  TestFlight. The packaging command is quoted:
  ```
  xcrun ba-package foundation-models package \
    --adapter-path aurelius1.fmadapter \
    --asset-pack-id fmadapter-aurel...
  ```
  → **`.fmadapter` bundle format** and an **`xcrun ba-package foundation-models`** subcommand.
  Neither appears in any transcript or doc we hold. Adapter training + delivery is a genuine,
  under-documented topic with a known failure mode.

**4. `SpotlightSearchTool` — two separate failures**
- Thread 838904: bare `SpotlightSearchTool()` + `LanguageModelSession(tools:)` →
  `Model Catalog error: Error Domain=com.apple.UnifiedAssetFramework Code=5000 "There are no
  underlying assets … for asset set com.apple.modelcatalog"` on macOS 27 beta 4, "although model is
  available". Suggests the tool pulls a **separate model asset** that may not be provisioned.
- Thread 837226: following session 246, the tool **isn't invoked at all** — responses aren't
  grounded; developer resorted to `GenerationOptions(toolCallingMode: .required)` as a probe.
  → confirms `toolCallingMode` lives on `GenerationOptions` when not using a profile, matching
  session 242.

**5. Image input limits**
- Thread 838613: model reliably *lists* objects in an image but **bounding boxes / coordinates are
  not reliable**. Practical takeaway for a guide: for spatial localization use Vision or a detection
  model (e.g. the `CoreAIObjectDetection` product / YOLO recipe), not the LLM.

**6. PCC economics and eligibility**
- Thread 835974: quota API is **too coarse** — only "reached" / "below" / "approaching". Developers
  want real numbers to build a usage UI. Confirms and sharpens the session-319 material.
- Thread 834749: a standard Developer Program account apparently **cannot apply directly**; asks
  whether a specific plan is needed for App Store approval.
- Thread 835897: the **< 2M downloads** gate is **lifetime**, not annual — a developer with 180k
  units in the last year is excluded because of pre-2015 success. (Session 241 said "2 million
  first time downloads"; the forum reading is *lifetime*. **Flag this as needing verification** —
  it materially changes eligibility advice.)

**7. Toolchain / SDK breakage**
- Thread 835987: watchOS 27 Beta 2 —
  `FoundationModels.swiftmodule/arm64e-apple-watchos.swiftinterface:6:15 Unable to resolve module
  dependency: 'CoreImage'`.
- Thread 835165: `SkillActivation` APIs from foundation-models-utilities fail to build on Xcode 26
  beta. (Consistent with `MLXFoundationModels` requiring the 27 SDK — **SDK-version gating is a
  cross-cutting theme.**)
- Thread 836264: developer watched session 339, saw `import MLXFoundationModels`, and **could not
  find the framework anywhere** — "there are even no BETA branches on the MLX framework".
  ✅ **I can answer this from my own spot-check:** it is a library target inside
  **`ml-explore/mlx-swift-lm`** (`Libraries/MLXFoundationModels`), requiring the 27.0 SDK. That this
  was a public point of confusion is strong evidence a guide on it is worth writing.

**8. Context management is a DIY problem people are solving in the wild**
- Thread 835927: a developer built and published `github.com/ricky-stone/FoundationContext`, which
  checks transcript token count via **`tokenCount(for:)`**, compacts at a threshold, and **retries
  once on `exceededContextWindowSize`**, then rebuilds a session from the compacted `Transcript`.
  They're asking Apple whether that's a sane use of the API.
  → Confirms real API names (`tokenCount(for:)`, `exceededContextWindowSize`) and shows that
  `foundation-models-utilities`' history modifiers exist precisely to replace this hand-rolling.
  Great narrative hook: "here's what people hand-rolled; here's the supported way now."

**9. Adjacent asks**
- Thread 834149: WWDC26 keynote announced a second-generation on-device model with **better speech
  generation**; developers are asking whether there's a **TTS / expressive-voice API**. No answer in
  the capture. → **Speech *synthesis* is a corpus gap; do not invent coverage for it.**

### Method note
These captures are RSS and the `content:encoded` bodies are **truncated with "..."** — so we have
the question but usually not the answers or Apple-engineer replies. To get authoritative answers we
must fetch the individual `developer.apple.com/forums/thread/<id>` URLs. Thread IDs worth pulling:
**838904, 838613, 838444, 837226, 836810, 836673, 836285, 835987, 835927, 835777, 835211, 835165,
834652, 829108**.

---

## C. RESOLVED: PCC eligibility — and a requirement no transcript mentions

The discrepancy I flagged (session 241 "less than 2 million first time downloads" vs forum thread
835897 reading it as a lifetime cap) is resolved. Verified 2026-07-27 via web search across Apple
developer pages and secondary coverage:

**Eligibility for no-cost PCC access is THREE conditions, not one:**
1. **Enrolled in the App Store Small Business Program** ← ⚠️ **stated in NO WWDC transcript we
   hold.** Sessions 241 and 319 both mention only the download threshold. This is a material
   omission — a developer can meet the download bar and still be ineligible.
2. **Fewer than 2 million *total first-time* App Store downloads** across any of their apps.
   So the forum poster in 835897 was reading it correctly: it is **cumulative/lifetime** first-time
   downloads, not a rolling annual figure. Their complaint (180k units last year but excluded
   because of pre-2015 success) is a genuine consequence of the policy, not a misunderstanding.
3. **The Private Cloud Compute entitlement assigned to the account** — applied for on the developer
   website.

Announced at **Platforms State of the Union, 9 June 2026**.

⚠️ `https://developer.apple.com/apple-intelligence/private-cloud-compute/` **404s**. The live path
is `https://developer.apple.com/private-cloud-compute/` (this is also the URL the forum poster in
thread 834749 cites). Use the latter in guides.

Sources: WWDC26 session 241 and 319 pages on developer.apple.com; developer.apple.com WWDC26
Apple Intelligence guide; secondary coverage corroborating the Small Business Program condition.
**Recommend one more direct confirmation from the Apple entitlement/application page before this
goes into a published guide** — the Small Business Program condition currently rests on secondary
sources plus the developer-site guide, not on a transcript quote.

**Guide implication:** any "should I use PCC?" decision section must lead with eligibility, because
for a large fraction of readers the answer is "you cannot", and the fallback path
(`ChatCompletionsLanguageModel` → your own server, or a third-party `LanguageModel` package with
your own billing) is a different guide entirely.
