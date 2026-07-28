# Missing Sessions — corpus gap closure

**Research notes (raw). Theme: `missing-sessions`.**

Seven sessions our 17-part guide series depends on were absent from the local transcript corpus.
All seven were obtained this session and saved. This file is the research-notes layer over them.

> ⚠️ **Provenance rule for this file.** Everything below comes from a page I fetched **this
> session**. Nothing is written from model memory. Fenced blocks marked **[VERBATIM — Apple code
> sample]** are copied character-for-character from the "Code Samples" block Apple publishes on the
> session page. Blocks marked **[RECONSTRUCTED]** are my reassembly from narration and are NOT
> Apple's text. Anything I could not confirm on a page I read is marked **UNVERIFIED**.

> ⚠️ **Transcript-file caveat.** The `.txt` files I saved are sentence-split renderings of the
> transcript prose Apple publishes on each session page. Apple's *code samples* are published
> separately from the transcript on those pages; I kept the `.txt` files prose-only to match the
> existing corpus format, and reproduced the code here instead. So: **the code in this file does
> not appear in the matching `.txt`** — cite this file for code, the `.txt` for spoken lines.

---

## Source inventory

Per the deliverable spec: for EACH target, the URL tried, whether it worked, and the saved path.

| # | Target (as briefed) | Actual session + title | URL tried | Result | Saved transcript |
|---|---|---|---|---|---|
| 1 | WWDC26 **343** — App Intents / `.system.searchInApp` | **343 — "Explore advanced App Intents features for Siri and Apple Intelligence"** (Antonio Cancio) | `https://developer.apple.com/videos/play/wwdc2026/343/` | ✅ **WORKED** — full transcript + 9 code samples | `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-343.txt` (219 lines) |
| 2 | WWDC26 **345** — App Intents, "2027 releases" wording | **345 — "Discover new capabilities in the App Intents framework"** (Moe) | `https://developer.apple.com/videos/play/wwdc2026/345/` | ✅ **WORKED** — full transcript + 7 code samples | `…/transcripts/wwdc2026-345.txt` (202 lines) |
| 3 | WWDC26 **240** — App Intents / Siri | **240 — "Build intelligent Siri experiences with App Schemas"** (Dan Niemeyer) | `https://developer.apple.com/videos/play/wwdc2026/240/` | ✅ **WORKED** — full transcript + 5 code samples | `…/transcripts/wwdc2026-240.txt` (256 lines) |
| 4 | WWDC26 **344** — App Intents | **344 — "Code-along: Make your app available to Siri"** (Justin) | `https://developer.apple.com/videos/play/wwdc2026/344/` | ✅ **WORKED** — full transcript; **NO published code-sample block** (code was narrated on-screen only) | `…/transcripts/wwdc2026-344.txt` (232 lines) |
| 5 | "What's new in image understanding" — number unknown | **237 — "What's new in image understanding"** (Megan Williams, Vision team) | `WebSearch` → `https://developer.apple.com/videos/play/wwdc2026/237/` | ✅ **WORKED** — full transcript + 5 code samples | `…/transcripts/wwdc2026-237.txt` (176 lines) |
| 6 | "Explore distributed inference and training with MLX" — number unknown | **233 — "Explore distributed inference and training with MLX"** (Tatiana, MLX team) | `WebSearch` → `https://developer.apple.com/videos/play/wwdc2026/233/` | ✅ **WORKED** — full transcript + 8 code/shell samples | `…/transcripts/wwdc2026-233.txt` (176 lines) |
| 7 | "The M5 machine-learning talk" — number unknown | **Tech Talk 111432 — "Accelerate your machine learning workloads with the M5 and A19 GPUs"** (Zak, GPU Driver Performance) | Found via the *Related Videos* block on session 330's page → `https://developer.apple.com/videos/play/tech-talks/111432/` | ✅ **WORKED** — full transcript; code narrated, **no published sample block** | `…/transcripts/tech-talks-111432.txt` (347 lines) |

### Technique notes (for the next agent who has to do this)

- **`WebFetch` on `developer.apple.com/videos/play/wwdc2026/<n>/` works directly and is the best
  path.** It returns the complete transcript *and* Apple's published code-sample block with
  timestamps. No mirror needed. This is a change from the `/documentation/` situation.
- **`WebFetch` on `developer.apple.com/documentation/...` does NOT work** — those pages are
  client-rendered and WebFetch receives only the `<title>`. Confirmed twice this session on
  `/documentation/vision/barcodereadertool` and `/documentation/vision/ocrtool`.
- **`sosumi.ai` is the correct mirror for `/documentation/` paths** and worked every time
  (`https://sosumi.ai/documentation/vision/barcodereadertool`, `…/ocrtool`,
  `…/ocrtool/init(name:description:)`, `…/appintents/stringsearchcriteria`).
- I did **not** need `r.jina.ai` or `claude-in-chrome` for any of the seven. `sosumi.ai` for
  `/videos/` was never exercised because the direct fetch already worked.
- **Finding unknown session numbers:** the fastest route for #7 was *not* WebSearch (which surfaced
  only tangential results) but fetching the **session page of the session that cites it** and
  reading its *Related Videos* list. Session 330's page names
  `/videos/play/tech-talks/111432` explicitly.
- `https://developer.apple.com/wwdc26/guides/machine-learning/` is a good index — it enumerated 18
  ML-track sessions with numbers and titles in one fetch. **Tech Talks are not in it**, which is why
  #7 could not be found that way.

### Sessions NOT obtained

None. All seven targets were obtained in full.

---

## What this file resolves

| Open question from the brief | Status |
|---|---|
| `BarcodeReaderTool` / `OCRTool` declarations, argument schemas, output types | **PARTIALLY RESOLVED.** Struct declaration, availability, conformances, initializer signature with defaults, and prose descriptions of the outputs are now verified. The `Arguments` / `Output` associated types are **not published** on Apple's doc pages and remain a genuine gap. See §5.4–5.6. |
| `.system.searchInApp` — exact spelling, what it takes, how it differs from deprecated per-domain search | **RESOLVED.** Spelling confirmed verbatim from 343 transcript *and* from Apple's own published code sample for 343. Takes `StringSearchCriteria`. See §1.9. |
| MLX distributed — `mlx.launch`, hostfile format, JACCL / Thunderbolt RDMA, speedups | **RESOLVED IN FULL.** Hostfile JSON schema, `mlx.distributed_config` flags, RDMA enablement steps, both topologies, and three measured numbers. See §6. |
| TensorOps basics — corroborate/contradict "26.2 not 27", and "scale planes don't exist" | **PARTIALLY RESOLVED, AND OUR "26.2" IS WRONG IN DETAIL.** The M5 talk gives an explicit per-point-release feature ladder: 26.1, 26.3, 26.4 — and **no 26.2**. See §7.5, which is the most consequential correction in this file. |

---

## Table of contents

1. [WWDC26 343 — Explore advanced App Intents features for Siri and Apple Intelligence](#1-wwdc26-343--explore-advanced-app-intents-features)
2. [WWDC26 345 — Discover new capabilities in the App Intents framework](#2-wwdc26-345--discover-new-capabilities-in-the-app-intents-framework)
3. [WWDC26 240 — Build intelligent Siri experiences with App Schemas](#3-wwdc26-240--build-intelligent-siri-experiences-with-app-schemas)
4. [WWDC26 344 — Code-along: Make your app available to Siri](#4-wwdc26-344--code-along-make-your-app-available-to-siri)
5. [WWDC26 237 — What's new in image understanding](#5-wwdc26-237--whats-new-in-image-understanding)
6. [WWDC26 233 — Explore distributed inference and training with MLX](#6-wwdc26-233--explore-distributed-inference-and-training-with-mlx)
7. [Tech Talk 111432 — Accelerate your ML workloads with the M5 and A19 GPUs](#7-tech-talk-111432--accelerate-your-ml-workloads-with-the-m5-and-a19-gpus)
8. [Cross-cutting: contradictions and refinements to what we already believe](#8-cross-cutting-contradictions-and-refinements)
9. [Residual gaps](#9-residual-gaps)

---

# 1. WWDC26 343 — Explore advanced App Intents features

**Presenter:** Antonio Cancio, software engineer, App Intents team.
**Source:** `https://developer.apple.com/videos/play/wwdc2026/343/` — fetched this session.
**Transcript:** `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-343.txt`

Sample apps used throughout, all downloadable from the developer site:
**CosmoTunes** (music), **UnicornChat** (messaging), **CometCal** (calendar). CometCal is the same
app built in session 344; CosmoTunes is referenced by name from session 345. The three sessions
are deliberately a set.

Explicit prerequisite framing from the opening: *"This talk assumes a basic understanding of App
Intents and App Schemas."*

## 1.1 Version gate — the exact wording

343 closes with:

> **343** — *"With the **27 releases**, Apple Intelligence is transforming what Siri can do, and App
> Intents puts that transformative power directly in your hands."*

Note the phrasing: **"the 27 releases"**, not "iOS 27". Session 240 uses the same construction
("In the **27 releases**, Siri is more capable…"). Session 345 uses **"our 2027 releases"**.
See §8.1 for why this matters.

## 1.2 Shaping the Siri conversation — custom responses

The design framing, which is the part that does not appear in written docs:

> **343** — *"Siri does the heavy lifting. It understands natural language, picks the right action,
> and crafts a helpful response. The App Intents framework gives you the tools to shape what Siri
> does, and **refine how it responds**."*

Baseline: return an empty `IntentResult` and *"This tells Siri to take care of the response when the
intent runs."* Siri authors the sentence.

To take it over, add `ProvidesDialog` and return an `IntentDialog` with **two** strings:

**[VERBATIM — Apple code sample, 343 @ 2:42]**
```swift
@AppIntent(schema: .audio.addToPlaylist)
struct AddToPlaylistIntent {

    func perform() async throws -> some IntentResult & ProvidesDialog {
        // Adds song to playlist and responds
        return .result(
            dialog: IntentDialog(
                full: """
                      Added \(song.title) to the \
                      \(playlist.title) mix tape.
                      """,
                supporting: "Added"
            )
        )
    }
}
```

The `full:` / `supporting:` split and the rule governing it — this is a real recommendation and
easy to get wrong:

> **343** — *"Siri can show the **supporting** string with UI, and read the **full** dialog on
> voice-only devices like AirPods. **Because of this, the full string should describe what happened
> on its own.**"*

So `supporting:` is the caption that sits next to a visual; `full:` must be self-sufficient audio.
The presenter's motivation for customizing at all is brand vocabulary: *"I call songs **tracks** and
playlists **mix tapes**."*

## 1.3 Asking a question mid-`perform` — `requestValue`

> **343** — *"But what if you want to ask people a question **while your intent is running**? A
> well-placed clarifying question lets people finish the action they meant to take. To ask a
> question **before your intent result**, use a dialog request within your perform method."*

**[VERBATIM — Apple code sample, 343 @ 3:42]**
```swift
@AppIntent(schema: .clock.createTimer)
struct CreateTimerIntent {
    // MARK: Schema Parameters
    var duration: Duration
    var label: String?
    var isSleepTimer: Bool

    func perform() async throws -> some ReturnsValue<TimerEntity> {
        // Checks active timers and requests label parameter
        label = try await $label.requestValue(
            """
            You already have a timer running. \
            What should we call this one?
            """
        )
        return .result(value: timerEntity)
    }
}
```

API facts extractable from this:
- The `@AppIntent` macro projects each parameter as `$name`, and `$name.requestValue(_:)` is an
  `async throws` call returning the resolved value.
- The schema `.clock.createTimer` has parameters `duration: Duration`, `label: String?`,
  `isSleepTimer: Bool` — a **concrete schema parameter list**, useful independent of the topic.
- `Duration` as a schema parameter type corroborates 345's claim that `Duration` is now a
  natively-supported `@Parameter` type (§2.9).

Other dialog-request kinds exist but were not shown: *"If you want to ask people to **choose from a
list of items**, or ask for a **confirmation**, check out the sample app and documentation to learn
about other kinds of dialog requests."* — **UNVERIFIED**: their exact symbol names.

## 1.4 `DisplayRepresentation` — where it is actually consumed

This is the highest-leverage list in the session because it justifies the effort:

> **343** — *"Entity display representation can be used in **responses**, like when an entity has
> been created or updated. They are also used when **asking someone to choose between similar
> entities**, or when **answering questions about content in your app**. **Spotlight and Shortcuts**
> can use them, too."*

And later, a fourth consumer: **intent confirmations** (§1.7), and a fifth: the **onscreen-awareness
fast path** (§1.11).

**[VERBATIM — Apple code sample, 343 @ 4:26]**
```swift
// Enhanced DisplayRepresentation
@AppEntity(schema: .audio.song)
struct SongEntity {

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(
            title: "\(title)",
            subtitle: "\(artistName)",
            image: artworkImage
        )
    }
}
```

`DisplayRepresentation(title:subtitle:image:)` — title is a `LocalizedStringResource`-style
interpolation; subtitle and image are the enrichment.

## 1.5 Custom snippet views — `ShowsSnippetView`

**[VERBATIM — Apple code sample, 343 @ 5:05]**
```swift
@AppIntent(schema: .audio.addToPlaylist)
struct AddToPlaylistIntent {

    var audioEntity: AudioEntity
    var playlist: PlaylistEntity

    func perform() async throws -> some IntentResult & ProvidesDialog & ShowsSnippetView {
        // Adds to playlist and shows dialog and snippet
        let view = PlaylistSnippetView(
            playlist: updatedEntity,
            tracks: updated.tracks
        )
        return .result(dialog: dialog, view: view)
    }
}
```

Return-type composition: `some IntentResult & ProvidesDialog & ShowsSnippetView`, and the matching
`.result(dialog:view:)` factory. Note the schema `.audio.addToPlaylist` declares parameters
`audioEntity: AudioEntity` and `playlist: PlaylistEntity` — and `AudioEntity` is a **`UnionValue`**
(§1.10), so a schema parameter can itself be a union.

### The recommendation block — verbatim, because it is the rare "don't" list

> **343** — *"When approaching customization, **test your intents and decide where customization
> actually makes sense for your app**. Make sure your responses are accurate and **sound natural
> across all platforms, including voice-only devices like AirPods**. Remember to **ask clarifying
> questions sparingly to avoid friction**. Finally, use custom visuals to bring your app's identity
> to Siri, **keeping in mind how they'll scale across the ecosystem**."*

## 1.6 Interaction Donations

The problem statement is precise and worth quoting because it draws the boundary of what the system
learns for free:

> **343** — *"When people interact with your app **through Siri or Shortcuts, the system already
> knows about it**. But, Apple Intelligence **can't learn from actions people take through your
> app's UI** without your help. That's where donations come in."*

Mechanism:

> **343** — *"Each donation is a hint that a person took a specific action in your app's UI. The
> system stores these as **schema-conforming App Intents in a temporary transcript**, giving Siri
> the context it needs to make smarter decisions."*

Two distinct payoffs, both named:

1. **Preference learning / app disambiguation.** *"After messaging them frequently in the app,
   eventually, when someone says: 'Send a message to a contact from the Home Screen,' Siri might
   **infer the right app** to use for that contact."*
2. **Live activity awareness.** *"Interaction Donations also keep Siri aware of **ongoing
   activities** in your app."* The Maps example: a `NavigationSession` started in the app's UI is
   donated; the person then asks Siri to add a stop, and *"Thanks to the Interaction Donation, Siri
   can know **what NavigationSession is active** in the app."*

**The scope of #2 is explicitly enumerated — this is a hard limit, not a general capability:**

> **343** — *"This pattern applies to intents that **start or stop NavigationSessions in the Maps
> domain**, and **stop, start, pause, or lap stopwatches in the Clock domain**."*

**[VERBATIM — Apple code sample, 343 @ 7:44]**
```swift
@ModelActor
actor ModelManager {
    func sendMessage(_ /* ... */, donateIntent: Bool = false) async throws -> [Message.ID] {

        // Donate intent with parameters and result so Siri can learn user preferences
        if donateIntent {
            let intent = SendMessageIntent()
            intent.destination = .recipients(conversation.recipients.map(\.entity))

            let result = messages.map(\.entity)
            Task {
                try await IntentDonationManager.shared.donate(
                    intent: intent,
                    result: .result(value: result)
                )
            }
        }
    }
}
```

API surface: `IntentDonationManager.shared.donate(intent:result:)`, `async throws`. The result is
passed as `.result(value:)` — i.e. **you donate the outcome, not just the invocation**.

Design pattern worth copying: the shared helper takes a `donateIntent: Bool = false` flag so the
same code path serves both the UI and the intent, and only the UI call site donates. Rationale
verbatim: *"Apple Intelligence **already learns from Siri interactions**, so I only need to donate
**UI** interactions."*

### ⚠️ The anti-spam warning

> **343** — *"Your interaction donations should accurately represent real user behavior in your app.
> **If your app donates excessively, the system may ignore those donations.**"*

That is a silent-degradation failure mode with no error surface. Flag it in the guide.

## 1.7 Confirmations and `OwnershipProvidingEntity`

The security framing, verbatim:

> **343** — *"Asking people to confirm that the action looks right keeps them informed and protects
> them from **unintended side effects, which are a known risk with Large Language Models**."*

The system's default policy, stated plainly:

> **343** — *"**By default, Siri assumes your entities are private to the person, and may skip
> confirmations for them.**"*

So the *absence* of the protocol is a decision, not a neutral default. To opt in:

**[VERBATIM — Apple code sample, 343 @ 10:03]**
```swift
// Informs system if entity is public or shared with others
@AppEntity(schema: .calendar.event)
struct EventEntity: OwnershipProvidingEntity {

    var ownership: EntityOwnership {
        // isShared used to compute ownership state: .shared, .public, or .unknown
        attendees.isEmpty ? .unknown : .shared
    }
}
```

**New API confirmed:**
- protocol **`OwnershipProvidingEntity`**
- requirement **`var ownership: EntityOwnership`**
- **`EntityOwnership`** cases named in Apple's own comment: **`.shared`**, **`.public`**,
  **`.unknown`**. (There is no `.private` case in the comment — "private" is the *implicit* default
  when you don't adopt the protocol. **UNVERIFIED** whether a `.private` case also exists.)

Scoping and freshness recommendations, both explicit:

> **343** — *"**Only add the protocol to entities that people can share or make public in your app.**
> Then, provide the ownership state. **Keep the ownership state up to date whenever the system
> requests an entity from your app.** This ensures Siri has the necessary information when deciding
> to confirm."*

Worked example of the policy: *"Siri may **not** confirm when I update a personal event, but it
**may** confirm when I ask it to update Crew Lunch since I'm updating an event **with attendees**."*
And confirmations reuse your `DisplayRepresentation` as their visual.

Cross-reference given: **"Secure your app: Mitigate risks to agentic features."** — a session title
we should check is in the corpus.

## 1.8 Three retrieval paths, and how to choose

343 frames content discovery as exactly three paths: **semantic index**, **structured search**,
**in-app search**. The decision rule is stated as a data-shape question:

> **343** — *"you might **not** index your entities if your content dataset is **large, lives on a
> server, or changes too frequently** to index ahead of time. For example, I decided to index all
> the app's **playlists, but not songs**."*

### Path 1 — `IndexedEntity` + Spotlight

**[VERBATIM — Apple code sample, 343 @ 11:30]**
```swift
// Indexing IndexedEntity with CSSearchableIndex
struct EntityIndexingHelper {
    // Indexes playlist entities
    func indexPlaylist(_ playlist: Playlist) async throws {
        let entity = PlaylistEntity(playlist: playlist)
        try await CSSearchableIndex(name: indexName)
            .indexAppEntities([entity])
    }
}
```

`CSSearchableIndex(name:).indexAppEntities(_:)` — `async throws`.

Semantic search is **not universal** — it is domain-gated:

> **343** — *"**And depending on the App Intents domain**, indexing entities in Spotlight provides
> **semantic search** capabilities."*

That qualifier ("depending on the App Intents domain") is a real constraint we should not smooth
over. Adopting `IndexedEntity` in a domain Apple hasn't modelled may give you lexical Spotlight
without semantics. **UNVERIFIED**: which domains get semantics.

Index-maintenance rules, verbatim:

> **343** — *"**Index new entities** as people add content to your app. **Update existing entries
> when key properties change, especially those used in your display representation.** When people
> remove content, **delete those index entries** too."*

### New this year: `IndexedEntityQuery`

> **343** — *"**Spotlight may need your app to reindex its entities.** Your app can support
> reindexing by adopting the new **`IndexedEntityQuery`**. … **If your project already supports
> reindexing with Core Spotlight-level APIs, you do not need to define an `IndexedEntityQuery`.**"*

That second sentence is the useful one — it is an either/or, not an additional requirement.

### Path 2 — `IntentValueQuery` (structured search)

> **343** — *"`IntentValueQuery` is suitable **if you don't index all your entities ahead of time**.
> This is very similar to `EntityQuery`. **The key differences are that your app receives a
> structured search input from the system, and you can return more than one entity type.**"*

**[VERBATIM — Apple code sample, 343 @ 13:38]**
```swift
// Structured search of songs and playlists
struct AudioIntentValueQuery: IntentValueQuery {

    // AudioSearch, IntentPerson, and other system types may be supported as input
    func values(for input: AudioSearch) async throws -> [AudioEntity] {
        switch input.criteria {
        case .searchQuery(let query):
            return try await searchResults(for: query)
        case .unspecified:
            return try await likedSongResults()
        // ... also a .url case
        }
    }
}
```

Confirmed API shape:
- `protocol IntentValueQuery` with `func values(for input:) async throws -> [Entity]`
- The input is a **system-provided structured search type**. Named examples: **`AudioSearch`**,
  **`IntentPerson`**. Apple's own comment says *"and other system types may be supported as input"*.
- `AudioSearch` has a **`.criteria`** property, an enum with at least: **`.searchQuery(String)`**,
  **`.unspecified`**, **`.url`**.
- The return element type here is `AudioEntity`, *"a `UnionValue` type that includes both songs and
  playlists"* — this is the "return more than one entity type" mechanism.

Semantics of each case, from the narration:
- `.searchQuery` — *"contains the **relevant part of what the person said**"* (i.e. Siri has already
  stripped the carrier phrase).
- `.unspecified` — *"'Play CosmoTunes' which isn't specific about what I want to play. In that case,
  the app jumps straight into playing songs I've previously liked."*
- `.url` — *"for when someone references a **link** from your app. Like: 'Play that playlist Glow
  sent me.'"*

*"Check out the documentation for the full set of `AudioSearch` criteria."* — **UNVERIFIED**: the
complete case list.

## 1.9 ✅ `.system.searchInApp` — RESOLVED

This is one of the four open questions. Both the transcript **and** Apple's published code sample
for this session confirm it.

### The exact spelling and the deprecation relationship — verbatim

> **343** — *"To do this, I'll adopt the system **`.searchInApp`** schema. **The `.system` search
> schema introduced in iOS 17 is now named `.system.searchInApp`.** It is part of the **System App
> Schema domain**, and it lets people search in your app with Siri, **no matter which other domains
> you adopt, and even if you don't index your entities**."*

That sentence answers all three sub-questions:

1. **Exact spelling:** `.system.searchInApp` — used as `@AppIntent(schema: .system.searchInApp)`.
2. **How it differs from the deprecated per-domain search intents:** it is not a *different* schema
   from `.system.search` — **it is the same schema, renamed.** The iOS 17 `.system` search schema
   *"is now named `.system.searchInApp`"*. This is a rename, not a replacement with new semantics.
3. **What it takes:** a `StringSearchCriteria`.

### The code

**[VERBATIM — Apple code sample, 343 @ 14:49]**
```swift
// Intent that re-runs the Siri search in app
@AppIntent(schema: .system.searchInApp)
struct SearchAudioLibraryIntent {

    var criteria: StringSearchCriteria

    func perform() async throws -> some IntentResult {
        // Perform in-app search with Siri search string
        navigation.searchText = criteria.term
        navigation.selectedTab = .library
        return .result()
    }
}
```

Note Apple's own header comment: **"Intent that re-runs the Siri search in app."** That is the
mental model — Siri hands you back its own query string and gets out of the way.

### `StringSearchCriteria` — verified independently

Fetched `https://sosumi.ai/documentation/appintents/stringsearchcriteria` this session:

```swift
struct StringSearchCriteria
```
- **Availability:** iOS 17.2+, iPadOS 17.2+, Mac Catalyst 17.2+, macOS 14.2+, tvOS 17.2+,
  watchOS 10.2+. (visionOS listed but with an undefined version.)
- **Instance property:** `term` — *"The string value used for matching items in the application"*.
- **Initializer:** `init(term:)`
- **Type aliases:** `Specification`, `UnwrappedType`, `ValueType`
- **Type property:** `defaultResolverSpecification`
- **Conformances:** `Copyable`, `Equatable`, `Escapable`, `Hashable`, `IntentValueConvertible`,
  `IntentValueExpressing`, `SearchCriteria`, `Sendable`, `SendableMetatype`
- Description: *"A type that tells your app to match its items against a provided string."*

**Note the availability: `StringSearchCriteria` is an iOS 17.2 type, not a 27 type.** The *type* is
old; only the schema *name* `searchInApp` is new. That is consistent with "the iOS 17 schema is now
renamed", and it strengthens the case that this is a pure rename.

### Behaviour contract

> **343** — *"Siri calls this intent with **the same string it searched for**, and the intent's
> perform method **finds and shows those results in the app**."*

And the motivation, which is the "why not just let Siri render it" answer:

> **343** — *"Siri can display a list of entity search results. **That's a nice default. But I spent
> a lot of time crafting the app's own search experience, and I'd love to show these results
> there.**"*

### ✅ Correction to our existing note

`notes/web/app-intents-siri-schemas.md:858` currently carries:

> *"**UNVERIFIED naming detail.** `.system.searchInApp` comes from session 343's transcript content.
> The domain page I fetched (`app-schema-domain-system-and-in-app-search`) listed only `open` and
> `search` (deprecated) as leaf symbols and did not list `searchInApp`. … Likely a doc-page lag."*

**That UNVERIFIED flag can now be downgraded.** The spelling is confirmed by a *second, independent
artifact*: Apple's own published code-sample block for session 343 (timestamp 14:49), which is
separate from the transcript prose. Two independent renderings on the same page agree. The
doc-page-lag hypothesis in that note is now the most likely explanation for the domain page's
omission. I would still not call it *documentation*-verified, because I could not find a
`/documentation/` page for `searchInApp` — see §9.


## 1.10 `UnionValue` in the wild

343 uses `AudioEntity` as *"a `UnionValue` type that includes both songs and playlists"* without
showing its declaration. Session 345 shows the declaration form (§2.10). Cross-referencing the two
gives us a complete picture: `@UnionValue` enums are usable both as **`IntentValueQuery` return
element types** (343) and as **`@Parameter` input types** (345). 345 explicitly frames the latter as
new: *"With `@UnionValue` **supporting input parameters**, I can use one widget for both."* —
implying output/return use predates it.

## 1.11 Onscreen awareness — four APIs, and when to use each

The capability statement first, because it sets the bar:

> **343** — *"When people start a Siri request, Siri has an understanding of text on screen, **but
> it's limited to exactly what's in the pixels**. For example, Siri **can't act on** the tracks
> shown, and it **may not be able to tell you about the artist** because the artist isn't currently
> shown on screen."*

So without adoption you get OCR-grade awareness: no actions, no offscreen properties.

> **343** — *"Adopting onscreen awareness APIs provides Siri with additional context of **what
> entities are on screen, and where they are on screen**."*

### The four APIs and their selection rule

| API | Use when | Evidence |
|---|---|---|
| **`NSUserActivity`** (`.userActivity` modifier) | *"the view representing your **primary** onscreen content"* — one dedicated thing | `NowPlayingView` |
| **View Entity annotation** (`.appEntityIdentifier`) | *"when the entity is **one item among many** on screen"* | `AlbumView` — *"because both the album and the containing tracks are visible"* |
| **Collection annotation** (`.appEntityIdentifier(forSelectionType:)`) | lists/collections displaying many entities | `PlaylistDetailView` |
| **Custom canvas view annotation** | non-standard drawn subviews | `PianoRollView` |

Apple's own starting advice: *"When adopting onscreen awareness, the **`NSUserActivity` and View
Annotation APIs are where you should start**."*

**[VERBATIM — Apple code sample, 343 @ 16:27]**
```swift
// (a) Single primary entity on screen — NSUserActivity
struct NowPlayingView: View {
    @Environment(PlaybackController.self) private var playback

    var body: some View {
        VStack {
            // Player UI
        }
        .userActivity("cosmotunes.nowPlaying", isActive: playback.currentTrack) { activity in
            activity.title = playback.currentTrack?.title
            activity.appEntityIdentifier = EntityIdentifier(
                for: SongEntity.self,
                identifier: playback.currentTrack.id
            )
        }
    }
}

// (b) One entity among many — View Entity annotation
struct AlbumView: View {
    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            // ...
        }
        .appEntityIdentifier(
            EntityIdentifier(for: AlbumEntity.self, identifier: session.id.uuidString)
        )
    }
}

// (c) Lists and collections — Collection annotation
struct PlaylistDetailView: View {
    var body: some View {
        List {
            ForEach(playlist.tracks) { track in
                PlaylistTrackRow(track: track)
            }
        }
        .appEntityIdentifier(forSelectionType: GeneratedTrack.ID.self) { trackID in
            EntityIdentifier(for: SongEntity.self, identifier: trackID)
        }
    }
}
```

**Confirmed API surface:**
- `EntityIdentifier(for: <EntityType>.self, identifier: <id>)` — the universal currency type. Note
  `AlbumView` passes `session.id.uuidString` (a `String`) while `NowPlayingView` passes
  `playback.currentTrack.id` directly, so `identifier:` is generic over the entity's `ID`.
- `NSUserActivity.appEntityIdentifier` — **singular**, one identifier.
- SwiftUI `.appEntityIdentifier(_:)` — view modifier taking one `EntityIdentifier`.
- SwiftUI `.appEntityIdentifier(forSelectionType:_:)` — takes a selection-ID metatype and a closure
  mapping each selection ID to an `EntityIdentifier`.
- SwiftUI `.userActivity(_:isActive:_:)` — standard, with the identifier assigned in the closure.

### ⚠️ The collection-annotation rationale — two distinct benefits, both non-obvious

> **343** — *"Collection annotations help me avoid the overhead of attaching an annotation to every
> single row. Instead, **the system fetches identifiers lazily, as it needs them**. Collection
> annotations **also let Siri discover entities that have been selected and scrolled off screen.
> Per row annotations disappear as soon as the view leaves the view hierarchy.**"*

The second half is the sharp edge: per-row `.appEntityIdentifier` in a `ForEach` is *not* equivalent
to the collection form, because SwiftUI recycles rows. If a user selects something and scrolls away,
per-row annotation loses it. This is exactly the kind of thing that never makes it into docs.

### UIKit/AppKit equivalents

> **343** — *"UIKit and AppKit also support all of the onscreen awareness APIs. Check out the
> documentation for: **`AppEntityAnnotatable`**, **`UICollectionViewAppIntentsDataSource`**, and
> **`appEntityUIElementProvider`**."*

Three named symbols, unverified beyond the mention. Cross-reference given: *"Modernize your UIKit
app"* — *"to learn more about how these entity annotations help power **contextual menu items** in
UIKit apps."*

## 1.12 ⚠️ The onscreen-awareness performance trap — `displayRepresentations(for:requestedComponents:)`

This is the single most actionable performance item in 343 and it is easy to miss because it arrives
after the API tour.

> **343** — *"After adopting onscreen awareness, some of the app's views show many entities at once.
> Siri needs to **quickly** understand if the on-screen entities relate to a request. For example,
> someone asks Siri to play the third one. **If Siri can't understand my on-screen entities quickly
> enough, it may ask to clarify or play something else entirely. People can abandon the request when
> that happens.**"*

The fix:

**[VERBATIM — Apple code sample, 343 @ 17:23]**
```swift
// Component-based display representation queries
extension PlaylistQuery {
    func displayRepresentations(
        for identifiers: [PlaylistEntity.ID],
        requestedComponents: DisplayRepresentation.Components = .text
    ) async throws -> [PlaylistEntity.ID: DisplayRepresentation] {
        let entities = try await model.playlistEntities(for: identifiers)

        // Fetch display representations for fetched entities
        var result: [PlaylistEntity.ID: DisplayRepresentation] = [:]
        for entity in entities {
            result[entity.id] = await entity.displayRepresentation(with: requestedComponents)
        }
        return result
    }
}
```

**Confirmed API:**
- `func displayRepresentations(for:requestedComponents:) async throws -> [ID: DisplayRepresentation]`
  — an optional `EntityQuery` requirement.
- **`DisplayRepresentation.Components`** — an options type; **`.text`** is a case and is the default
  value in Apple's signature. (**UNVERIFIED**: the other cases; `.image` is the obvious guess but I
  did not see it.)
- `entity.displayRepresentation(with: DisplayRepresentation.Components) async` — an async overload
  of the property.

Payoff, verbatim: *"when Siri is trying to understand the content on screen, it can **query just the
text representation** of the entity and **skip the overhead of fetching the full content from the
database**."*

## 1.13 Entity annotations on system integrations — Notifications, Now Playing, AlarmKit

The framing sentence is quotable and is the best one-line summary of the App Intents strategy in the
whole set of four sessions:

> **343** — *"your app entities act as a **universal language**. They let Siri understand not just
> what's on screen, but how **other system integrations and time-sensitive events** relate to your
> content."*

Three integrations, *"All three use the same pattern, and we call these **entity annotations**."*

**[VERBATIM — Apple code sample, 343 @ 21:07]**
```swift
// (a) User notifications
import AppIntents
import UserNotifications

func scheduleNotification(message: Message, author: Contact, conversation: Conversation) {
    let content = UNMutableNotificationContent()
    content.title = author.name
    content.body = message.body

    // Annotate with entity identifier
    content.appEntityIdentifiers = [
        EntityIdentifier(for: MessageEntity.self, identifier: message.id)
    ]
    // Schedule the notification
}

// (b) Now Playing — most specific to least specific
import NowPlaying

final class CosmoTunesMediaSession: MediaSessionRepresentable {
    var content: (any MediaContentRepresentable)? {
        var content = MusicContent(id: track.id.uuidString, songTitle: track.title /* ... */)
        content.appEntityIdentifiers = [
            EntityIdentifier(for: SongEntity.self, identifier: track.id),
            EntityIdentifier(for: ArtistEntity.self, identifier: track.session.artistName),
            EntityIdentifier(for: PlaylistEntity.self, identifier: currentPlaylist.id),
        ]
        return content
    }
}

// (c) AlarmKit
import AlarmKit

func scheduleAlarm(_ alarm: Alarm) async throws {
    let configuration = AlarmManager.AlarmConfiguration<CosmoTunesAlarmMetadata>.alarm(
        schedule: schedule,
        attributes: attributes,
        appEntityIdentifier: EntityIdentifier(for: AlarmEntity.self, identifier: alarm.id),
        stopIntent: DismissAlarmIntent(),
        secondaryIntent: SnoozeAlarmIntent(),
        sound: sound
    )
    // Schedule alarm
}
```

**Confirmed API surface — note the singular/plural split, which is a real API asymmetry:**

| Host type | Property / parameter | Cardinality |
|---|---|---|
| `UNMutableNotificationContent` | `.appEntityIdentifiers` | **array** |
| `MusicContent` (`NowPlaying`, via `MediaContentRepresentable`) | `.appEntityIdentifiers` | **array** |
| `AlarmManager.AlarmConfiguration<Metadata>.alarm(…)` | `appEntityIdentifier:` | **singular** |

Also newly surfaced from (c): `AlarmConfiguration.alarm(schedule:attributes:appEntityIdentifier:
stopIntent:secondaryIntent:sound:)` — a factory with `stopIntent:` and `secondaryIntent:`.
And (b) confirms `MediaSessionRepresentable` with a `var content: (any MediaContentRepresentable)?`
requirement, plus `MusicContent(id:songTitle:...)`.

### ⚠️ Two hard rules stated here

1. **Ordering is semantic for Now Playing.**
   > **343** — *"add them to the `appEntityIdentifiers` property **in order of most specific to
   > least specific**."*
   The sample's order — Song, Artist, Playlist — demonstrates it. This is what enables *"Play the
   live version"*.

2. **`TransientAppEntity` is banned from all three.**
   > **343** — *"Note, that with the **three entity annotation APIs** I'm describing, **you can't
   > use `TransientAppEntity`**. Transient entities are temporary model objects, so **they don't
   > have persistent identifiers**."*

   Cross-reference: session 344 (§4.4) makes `AttendeeEntity` a `TransientAppEntity` — so a CometCal
   attendee can never be an annotation target. That is a live design constraint, not trivia.

## 1.14 343's own recommended adoption order

Verbatim, in order, from the wrap-up — this is Apple's prioritization and is worth mirroring as the
guide's adoption ladder:

1. *"a great place to start is by **customizing your entity display representations**. They are used
   to display your entities across the system."*
2. *"From there, **add your entities to the semantic index, and keep the index up to date**, so Siri
   can always find your freshest content."*
3. *"You might also consider making your entities accessible through Siri with an
   **`IntentValueQuery` and in-app search**."*
4. *"**annotating your views, activities, and your existing system integrations** with entities."*
5. *"When you're ready, look into **donating UI interactions**."*

Donations are last. Notably the *display representation* is first — consistent with §1.4 and §1.12
showing it is consumed by five different subsystems.

---

# 2. WWDC26 345 — Discover new capabilities in the App Intents framework

**Presenter:** Moe, engineer, App Intents team.
**Source:** `https://developer.apple.com/videos/play/wwdc2026/345/` — fetched this session.
**Transcript:** `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-345.txt`

Sample app: the **Landmarks Travel Tracking app** from WWDC25's "Get to know App Intents".

## 2.1 ✅ The "2027 releases" wording — CONFIRMED VERBATIM

The brief flagged that our research notes 345 says "2027 releases" where the docs-updates page says
otherwise, and that exact wording matters. Here it is, from the first two sentences of the session:

> **345** — *"Hi, my name is Moe, an engineer on the App Intents team. I'm excited to share with
> you, the new App Intents capabilities we're introducing with **our 2027 releases**."*

And again, one paragraph later:

> **345** — *"**In our 2027 releases**, driven by your feature requests, we're bringing more control,
> more flexibility, and a significantly smoother developer experience."*

And a third time, in the `SyncableEntity` section:

> **345** — *"**With our 2027 releases**, Siri can continue conversations across devices — and your
> entities can be part of those conversations."*

**Three independent occurrences of "2027 releases" in session 345.** This is not a transcription
artifact.

### Cross-session comparison of the version phrasing

| Session | Phrase used | Occurrences |
|---|---|---|
| **345** | *"our **2027 releases**"* / *"In our 2027 releases"* / *"With our 2027 releases"* | 3 |
| **343** | *"With the **27 releases**"* | 1 (closing) |
| **240** | *"**In the 27 releases**, Siri is more capable, more contextual, and more personal"* and *"In the 27 releases, Siri takes a big step forward"* | 2 |
| **241** (already in corpus) | *"Our **2027 release** is all about integrations into and beyond the OS"* | 1 |

So the FM session (241) and the App Intents session (345) both say **"2027 release(s)"**; the two
Siri-facing sessions (240, 343) say **"the 27 releases"**. Both refer to the same OS generation
(iOS 27 / macOS 27). This is Apple presenters using the *calendar year of the release* and the
*version number* interchangeably.

**Interpretation for our guides:** *"2027 releases"* is **marketing-calendar phrasing for the 27
version family**, not a claim about a *later* release than 27. Anyone reading "2027" as "the year
after iOS 27 ships" is misreading it. If the docs-updates page says something numerically different
(e.g. "iOS 27.0"), **the two are not in conflict** — they are the same thing named two ways. That
resolves the discrepancy our research flagged, without needing to reconcile any factual difference.

Corroborating datapoint from a *different* artifact fetched this session: `BarcodeReaderTool` and
`OCRTool` — the two brand-new tools announced in the 2026 conference — are documented with
availability **"iOS 27.0+ Beta, macOS 27.0+ Beta"** (§5.5). So the WWDC26 conference ships into the
**27** OS family, which Apple also calls the **2027** releases. Consistent.

## 2.2 `ValueRepresentation` — sharing structured types across apps

The problem, precisely stated:

> **345** — *"Maps needs some **structured information** — a coordinate, an address, or something it
> can navigate to. But that kind of data **doesn't have an associated data format that can be put in
> a file or data**. The existing **file and data representations** work great for known formats like
> PDFs or images — **but not for structured types that don't have any**."*

> **345** — *"This is where **`ValueRepresentation`** comes in. It's a new representation type that
> lets you share **structured types that the system already understands**."*

**[VERBATIM — Apple code sample, 345 @ 0:01]**
```swift
struct LandmarkEntity: AppEntity, Transferable {
      var id: Int
      var landmark: Landmark  // contains CLLocationCoordinate2D

      static var transferRepresentation: some TransferRepresentation {
          ValueRepresentation(
              exporting: { entity in
                  PlaceDescriptor(
                      representations: [.coordinate(entity.landmark.locationCoordinate)],
                      commonName: entity.landmark.name
                  )
              }
          )
      }
  }

  // If the entity already has a PlaceDescriptor property, use a key-path — much less code:
  struct LandmarkEntity: AppEntity, Transferable {
      var id: Int
      @Property var placeDescriptor: PlaceDescriptor

      static var transferRepresentation: some TransferRepresentation {
          ValueRepresentation(exporting: \.placeDescriptor)
      }
  }
```

**Confirmed API:**
- `ValueRepresentation(exporting:)` — two overloads: closure form and **key-path form**.
- It composes: *"I just need to add a `ValueRepresentation` **alongside any existing
  representations**."*
- `PlaceDescriptor(representations:commonName:)` from **GeoToolbox**, with
  `.coordinate(CLLocationCoordinate2D)` as a representation case.

The recommendation: *"If my entity already has a `PlaceDescriptor` `@Property`, I can **skip the
closure entirely and use a key-path**. Same result, much less code."*

### Relationship to 240's `IntentValueRepresentation`

Session 240 (§3.7) uses **`IntentValueRepresentation(exporting:)`** and
**`IntentValueRepresentation(exporting:importing:)`** for the same conceptual job (exporting a
`ContactEntity` as an `IntentPerson`). 345 uses **`ValueRepresentation(exporting:)`**.

⚠️ **These two names appear in two different sessions for what looks like the same role.** I did not
find a page that reconciles them. Possibilities: (a) they are distinct types with `ValueRepresentation`
being the general one and `IntentValueRepresentation` the App-Intents-scoped one; (b) one is an alias.
Marked **UNVERIFIED** — do not assert equivalence in the guide. See §9.

## 2.3 `RelevantEntities` — the third discovery mechanism

The gap it fills is argued carefully and is the reason this API exists:

> **345** — *"But what about that new playlist? **Nobody's searched for it in Spotlight since they
> don't know it exists.** And since **nobody's played it, there's no interaction to donate** either.
> You need a way to tell the system this playlist is relevant so it can surface it at the right
> moment."*

That is the **cold-start problem** for content discovery, stated explicitly. Spotlight indexing
requires user search intent; donation requires prior user behaviour. Neither works for new content.

**[VERBATIM — Apple code sample, 345 @ 5:18]**
```swift
// Suggest playlists for the workout session
  let playlistEntities = [dailyRun, runningMix]
  let workoutContext = AppEntityContext.audio(.workout(activityType: .running))

  try await RelevantEntities.shared.updateEntities(
      playlistEntities, for: workoutContext
  )
  
  // Clear all entities for a context
  try await RelevantEntities.shared.removeAllEntities(for: workoutContext)

  // Remove specific entities from a context
  try await RelevantEntities.shared.removeEntities(playlistEntities, from: workoutContext)

  // Or remove all entities across all contexts
  try await RelevantEntities.shared.removeAllEntities()
```

**Confirmed API surface:**
- `RelevantEntities.shared` — singleton.
- `updateEntities(_:for:) async throws`
- `removeAllEntities(for:) async throws`
- `removeEntities(_:from:) async throws`
- `removeAllEntities() async throws`
- **`AppEntityContext`** — a nested enum. One concrete path verified:
  `AppEntityContext.audio(.workout(activityType: .running))`. So contexts are **domain-scoped**
  (`.audio`) with a **situation** (`.workout`) carrying **parameters** (`activityType:`).
  **UNVERIFIED**: the full set of `AppEntityContext` domains and situations.

Lifecycle rule: *"**Entities stay registered until you remove them.**"* — there is no TTL. That is a
memory-management obligation on the app.

### The three-way decision rule — verbatim, and this is the money quote

> **345** — *"Use **Spotlight** when you want your content to be **searchable and retrievable by
> Siri**. Use **interaction donation** to teach Siri and the system **how people use your app** — so
> it can identify patterns and suggest actions people may want to repeat. And use
> **`RelevantEntities`** to hint to the system **which content is relevant in specific situations**
> — so the system can suggest it at the right moment."*

Three mechanisms, three distinct jobs: *findability*, *behavioural learning*, *situational
suggestion*. This is a clean taxonomy and should go straight into the guide.

The consumer surface shown was the **Fitness app's suggested-playlists list when setting up a running
workout** — i.e. `RelevantEntities` feeds *other apps'* suggestion UI, not just Siri.

## 2.4 `EntityCollection` — the parameter-resolution performance cliff

This section explains an implicit cost in App Intents that is otherwise invisible.

> **345** — *"**Before an intent runs, the system resolves every entity.** That means **calling the
> entity query to populate all of its properties**, so the intent has everything it may need. For
> most intents, that's exactly what you want. But in my case, this meant **resolving hundreds or
> thousands of photo entities**, even though **my code only needs the entity ID** to update my data
> model."*

> **345** — *"**`EntityCollection`** fixes this. It's a new type that **stores an array of entity
> identifiers, instead of the fully resolved entities**. When you use `EntityCollection` as your
> parameter type, the system **passes just the identifiers** to the intent's perform method,
> **without resolving the full entities**."*

**[VERBATIM — Apple code sample, 345 @ 7:15]**
```swift
struct TagPhotosIntent: AppIntent {
      static let title: LocalizedStringResource = "Tag Travel Photos"

      @Parameter var photos: EntityCollection<PhotoEntity>   // was: [PhotoEntity]
      @Parameter var tag: String

      func perform() async throws -> some IntentResult {
          modelData.tagPhotos(ids: photos.identifiers, tag: tag)   // was: tagPhotos(photos, tag: tag)
          return .result()
      }
  }
```

**Confirmed API:** `EntityCollection<E>` generic over the entity type, with an **`.identifiers`**
property. Drop-in replacement for `[E]` as a `@Parameter` type.

**Measured claim:** *"I built a Shortcut to find and tag **1000 photos**. First, with a regular
array of photo entities. Then with `EntityCollection`, which was **almost instant**."* — Apple gives
no absolute numbers, only the qualitative contrast. Treat "almost instant" as the ceiling of what we
can claim.

Adoption criterion, distilled: **use `EntityCollection` whenever `perform` only needs IDs.** The
cost you avoid is N entity-query round trips, each of which may hit your database.

## 2.5 `SyncableEntity` — cross-device Siri conversations

New capability claim, and its consequence:

> **345** — *"With our 2027 releases, **Siri can continue conversations across devices** — and your
> entities can be part of those conversations."*

The failure mode:

> **345** — *"If I ask Siri on my iPhone to add a photo to an album, then switch to my other device
> and ask Siri to tag that photo — **Siri might not be able to find that photo**. … Your entity's ID
> **might be generated locally on each device**. Local IDs work great on the device they were created
> on. **But each device generates its own local IDs. So the same entity can end up with a different
> ID on each device.**"*

**[VERBATIM — Apple code sample, 345 @ 10:14]**
```swift
// If your ID is already stable across devices (server UUID, CloudKit record ID):
  struct PhotoEntity: AppEntity, SyncableEntity {
      var id: Int  // Already stable across devices — that's it
  }
  
  // If you use local IDs, pair a local and a stable ID:
  struct PhotoEntity: AppEntity, SyncableEntity {
      var id: SyncableEntityIdentifier<String, String>

      init(localID: String, stableID: String) {
          self.id = SyncableEntityIdentifier(local: localID, stable: stableID)
      }
  }
```

**Confirmed API:**
- protocol **`SyncableEntity`** — *"it **declares to the system** that your entity's ID is stable and
  can be used across devices."* Note it is a **declaration**, not a synchronization mechanism. The
  app still owns getting the IDs stable.
- **`SyncableEntityIdentifier<Local, Stable>`** — two generic parameters, `init(local:stable:)`.
- Division of labour, verbatim: *"**On-device, your code uses the local ID. And across devices, the
  system uses the stable one.**"*

Named sources of stable IDs: *"That could come from **your server, or from CloudKit record IDs**."*
Named source of unstable IDs: *"local identifiers, like **CoreData row IDs**."*

⚠️ **Adoption trap:** conforming to `SyncableEntity` with a locally-generated `id` and no
`SyncableEntityIdentifier` is a *lie to the system* that will compile fine. The protocol is a
promise; nothing validates it.

## 2.6 Native `@Parameter` types

> **345** — *"When you declare a `@Parameter`, the system gives you a **native picker, Siri
> understanding, and localization for free**. We're extending that same support to more native
> types. We're adding native support for **`Duration`**, so no more building custom time pickers.
> And **`PersonNameComponents`** for structured name input instead of a plain string. **And more.**"*

Two types named explicitly: **`Duration`**, **`PersonNameComponents`**. "And more" was not
enumerated — **UNVERIFIED**: the full list.

Corroboration for `Duration`: session 343's `.clock.createTimer` schema declares
`var duration: Duration` (§1.3). Corroboration again in session 344: CometCal's event alarms union
includes `Duration` (§4.5).

Payoff restated: *"Each one gets a **native picker** and works **everywhere your intent does — Siri,
Shortcuts and Widgets**."*

## 2.7 `@UnionValue` as an input parameter

> **345** — *"A union value is a **Swift enum where each case wraps a different type**, letting a
> single parameter represent one of several options."*

> **345** — *"With `@UnionValue` **supporting input parameters**, I can use **one widget for
> both**."*

**[VERBATIM — Apple code sample, 345 @ 11:58]**
```swift
@UnionValue
  enum TravelGalleryContent {
      case landmarkCollection(LandmarkCollectionEntity)
      case photoAlbum(PhotoAlbumEntity)

      static let typeDisplayRepresentation: TypeDisplayRepresentation = "Travel Gallery"
      static let caseDisplayRepresentations: [Cases: DisplayRepresentation] = [
          .landmarkCollection: "Landmark Collection",
          .photoAlbum: "Photo Album"
      ]
  }
```

**Confirmed API:**
- macro **`@UnionValue`** on an enum whose cases each wrap exactly one type.
- What the macro generates, verbatim: *"The macro generates everything the system needs — **type
  information, case metadata, and picker support**."*
- **`static let typeDisplayRepresentation: TypeDisplayRepresentation`** — *"the label for the
  **overall type**"*.
- **`static let caseDisplayRepresentations: [Cases: DisplayRepresentation]`** — *"maps **each case
  to the name shown in the picker**"*. Note the key type is a macro-synthesized **`Cases`** type
  (referenced as `.landmarkCollection` / `.photoAlbum`), not the enum itself. That is a
  non-obvious detail worth capturing — the enum has payloads so it can't be `Hashable` trivially,
  hence a separate caseless `Cases` mirror.
- Both `TypeDisplayRepresentation` and `DisplayRepresentation` are `ExpressibleByStringLiteral` here.

Scope: *"this isn't limited to Widgets — `@UnionValue` parameters **work everywhere your intent
does, including the Shortcuts app**."*

## 2.8 `LongRunningIntent` — past the 30-second wall

The limit, stated as a hard number:

> **345** — *"When your intent runs — **from Siri, Shortcuts, or any system surface** — **it only has
> 30 seconds to finish**. That works for most everyday actions. But not every intent is that quick."*

> **345** — *"**`LongRunningIntent`** fixes this. It lets your intent **run beyond the 30-second
> limit** — and **manages the background task lifecycle of your app**. And as your intent runs,
> **progress updates appear automatically as a Live Activity**."*

**[VERBATIM — Apple code sample, 345 @ 13:41]**
```swift
struct UploadPhotoIntent: LongRunningIntent, CancellableIntent {
      static let title: LocalizedStringResource = "Upload Photo"

      @Parameter var photo: IntentFile
  
      func perform() async throws -> some IntentResult & ProvidesDialog {
          let result = try await performBackgroundTask {
              let chunks = calculateChunks(for: photo)
              progress.totalUnitCount = Int64(chunks)

              for chunk in 1...chunks {
                  try Task.checkCancellation()
                  try await uploadChunk(chunk)
                  progress.completedUnitCount = Int64(chunk)
              }
              return "Upload complete!"
          } onCancel: { reason in
              cleanup(for: reason)
          }
          return .result(dialog: "\(result)")
      }
  }
```

**Confirmed API:**
- protocol **`LongRunningIntent`** (appears to refine `AppIntent`; the sample does not also list
  `AppIntent`, so `LongRunningIntent` likely inherits it).
- protocol **`CancellableIntent`** with an **`onCancel`** handler — here supplied as the trailing
  closure of `performBackgroundTask`.
- **`performBackgroundTask { … } onCancel: { reason in … }`** — `async throws`, generic over the
  body's return type.
- **`progress`** — an implicit member, `totalUnitCount` / `completedUnitCount` as `Int64`. Provided
  because *"it builds on **`ProgressReportingIntent`**, I get a **built-in `progress` object**"*.

### ⚠️ The non-optional requirement

> **345** — *"**`LongRunningIntent` requires the intent to report progress**, so the system knows
> it's still working and hasn't stalled."*

Progress reporting is not a nicety here — it is the liveness signal. An intent that adopts
`LongRunningIntent` and never touches `progress` should be assumed to get killed.

### `CancellableIntent` and the cancellation reasons

> **345** — *"**`CancellableIntent`** lets your intent **clean up gracefully when cancelled** —
> whether **the person tapped cancel, the system timed out or needed to reclaim resources**. … the
> handler **gives me the reason**, and I can use it to **cleanup partial uploads or cancel in-flight
> requests**."*

Three cancellation causes named: user-initiated, system timeout, resource reclamation. The `reason`
parameter's type is **UNVERIFIED**.

UI consequence: *"there's a **stop button right on the Live Activity**, so the person can cancel it
at any time."*

### Background GPU — a genuinely notable capability

> **345** — *"`LongRunningIntent` also supports **background GPU access on supported devices** — for
> tasks like **photo processing or on-device inference**. **Just make sure to add GPU access to your
> app's entitlement.**"*

This matters for our FM/Core AI guides: it is a supported path to running **on-device inference from
a background App Intent**. Two gates: "supported devices" (unspecified) and a **GPU-access
entitlement** (name **UNVERIFIED**).

## 2.9 `ExecutionTargets` — choosing the process

The setup is a real architectural problem, not a toy:

> **345** — *"When your intents, entities, and queries live in a **shared package** like this —
> linked by your app and extensions — the system has to decide **which process runs each intent**
> when a request comes in. It picks a target based on **heuristics** like **if the app is already
> running, it prefers the app**. and **if not, it launches the extension**. **But sometimes that's
> not the right choice.**"*

The concrete failure: *"My widget shares the data model with the app — but **having two processes
write to the same data store can cause conflicts**. So I gave the widget **read-only** access and
the main app handles all the writes."*

**[VERBATIM — Apple code sample, 345 @ 16:54]**
```swift
// Write operation — needs the main app
  struct UpdateFavoriteIntent: AppIntent {
      static var allowedExecutionTargets: ExecutionTargets { .main }
  }

  // Standalone download — runs in the extension
  struct DownloadPhotoIntent: AppIntent {
      static var allowedExecutionTargets: ExecutionTargets { .appIntentsExtension }
  }

  // Display-only — runs in the widget extension
  struct GetLandmarkStatusIntent: AppIntent {
      static var allowedExecutionTargets: ExecutionTargets { .widgetKitExtension }
  }

  // Works in either — lets the system choose
  struct TagPhotosIntent: AppIntent {
      static var allowedExecutionTargets: ExecutionTargets { [.main, .appIntentsExtension] }
  }
```

**Confirmed API:**
- `static var allowedExecutionTargets: ExecutionTargets`
- **`ExecutionTargets`** is an **OptionSet-like** type — the last sample uses array-literal syntax
  `[.main, .appIntentsExtension]`.
- Cases confirmed: **`.main`**, **`.appIntentsExtension`**, **`.widgetKitExtension`**.

> **345** — *"With `ExecutionTargets`, you **override the system's heuristics** and control exactly
> which process handles your intent."*

## 2.10 345's own recommended next steps

Verbatim, in order:

1. *"add **`ValueRepresentation`** to your entities so they can carry structured data across apps."*
2. *"**Register relevant content** with the system — so it gets surfaced at the right moment."*
3. *"Adopt **`EntityCollection`** to make your intents faster when working with large numbers of
   entities."*
4. *"add **`LongRunningIntent`** to any intent that needs more than 30 seconds to finish."*

Cross-references named: *"Code-along: Make your app available to Siri"* (= 344) and *"Validate your
App Intents adoption with **AppIntentsTesting**"* (session number **UNVERIFIED** — not in the ML
guide index; it is an App Intents-track session).

---

# 3. WWDC26 240 — Build intelligent Siri experiences with App Schemas

**Presenter:** Dan Niemeyer, software engineer, **Swift Intelligence Frameworks team**.
**Source:** `https://developer.apple.com/videos/play/wwdc2026/240/` — fetched this session.
**Transcript:** `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-240.txt`

Sample app: **UnicornChat** (messaging; contacts Bubbles, Flare, Glow) — the same app 343 uses.

This is the **conceptual/overview** session of the App Intents set. 344 is its hands-on companion:
*"The companion video 'Build intelligent Siri experiences with App Schemas' covers the concepts…"*
(344's own words about 240).

## 3.1 The three new Siri powers

> **240** — *"This year, Siri becomes more powerful in **three key ways**."*

1. **Entity access.** *"Siri can now access your app's entities, the real meaningful content inside
   your app. This means people can ask questions like: 'When and where is my next meeting?' And Siri
   can answer directly by understanding **what a meeting is** in your app, **which meeting is
   relevant**, and **which properties to return**, like time and location."*
2. **Action taking.** *"Siri can take action using your app's intents. … **Siri handles the language
   understanding. Your app focuses on the action.**"*
3. **On-screen context.** *"people can say things like: 'Explain this text', or: 'Get me reviews for
   this product'."*

## 3.2 `AppEntity` — the conceptual definition

> **240** — *"App entities describe **three important things. What the thing is, how it's
> identified, and which properties matter**, like a title, a date, or some text."*

And the framing that prevents the most common misunderstanding:

> **240** — *"**They're not a new data model. They're a way of describing your existing content so
> the system can understand it.**"*

Worked mapping: *"If you have a calendar app, **each event** is an entity. If you have a mail app,
**each message** is an entity. And if you have a photos app, **each photo and each album** is an
entity."*

UnicornChat's nouns: **Contact, Conversation, Message** — *"All three are modeled as app entities
that conform to app schemas."*

## 3.3 Why a schema is required on top of an entity

> **240** — *"modeling an entity is the first step, but **on its own, that's not enough** for Siri to
> be able to find it or talk about it. For Siri to understand **what an entity is, what category of
> thing it represents**, your entity needs to conform to an **`AppSchema`**. … **Instead of treating
> your app like a black box, Siri can reason about what the user is talking about.**"*

## 3.4 Entity resolution — `IndexedEntity` vs `EntityStringQuery`

The semantic-search argument, with a concrete example:

> **240** — *"When someone says something like: **'The best windsurfing in Carmel'**, they're **not
> looking for an exact text match. They're expressing meaning.** To support that experience, Siri
> needs **more than string matching. It needs semantic search.** And that's exactly what
> `IndexedEntity` enables."*

> **240** — *"**'Show the messages with Flare about movies'** — that's **not a string match**. Siri
> can find messages that reference movie titles because it's performing a **semantic query** over
> UnicornChat's indexed messages."*

**[VERBATIM — Apple code sample, 240 @ 7:59]**
```swift
// Contributing message content to Apple Intelligence
  
  @AppEntity(schema: .messages.message)
  struct MessageEntity: IndexedEntity {

      // The text content of the message
      @Property(indexingKey: \.textContent)
      var body: AttributedString?
  }
```

**Confirmed API:** `@Property(indexingKey:)` — a key-path into (presumably) `CSSearchableItem`
attribute keys. *"The **`indexingKey`** tells Spotlight **which properties, like the message body,
should be searchable**."* Named key: **`\.textContent`**. Property type here is
`AttributedString?`.

Capability claim worth keeping: *"Once indexed, Siri can **search your content, reason over it, and
use it to answer questions, not just retrieve items**."*

### The fallback

**[VERBATIM — Apple code sample, 240 @ 8:36]**
```swift
// An interface that locates entities using arbitrary string input

  struct ContactQuery: EntityStringQuery {
      func entities(matching string: String) async throws -> [ContactEntity] {
          let predicate = #Predicate<Person> { person in
              person.name.localizedStandardContains(string)
          }
          let descriptor = FetchDescriptor<Person>(predicate: predicate)
          let matches = try modelContext.fetch(descriptor)
          return matches.map(\.entity)
      }
  }
```

`EntityStringQuery.entities(matching:) async throws -> [Entity]`.

The explicit trade-off, verbatim — this is the sentence to quote when advising:

> **240** — *"**You don't get semantic understanding, but you do get full control over how you search
> for and match your app's entities.**"*

Same "when you can't index" criteria as 343: *"Your dataset might be **large, lives on a server, or
changes too frequently** to index ahead of time."* — identical phrasing across 240, 343 and 345.
Apple is repeating a fixed formula; treat it as the official test.

## 3.5 App Intents vs App Schemas — the distinction, stated cleanly

> **240** — *"Just like entities use app schemas to be understood, **actions use schemas to become
> executable by Siri**. Think of schemas as **a specialization of App Intents**. **They're still App
> Intents, but shaped in a way that Siri knows how to process.**"*

> **240** — *"Schemas define **the kinds of actions Siri understands, the structure it expects, and
> how those actions map to natural language**."*

And on domains:

> **240** — *"schemas are grouped into **`AppSchema` domains**. Each domain represents a **category
> of tasks**, such as mail, photos, messages, and more. … Think of domains as **categories of
> contracts between your app and Siri**."*

The plain-App-Intent baseline is still valuable and 240 says so: *"When you define an app intent,
that action can show up across the system in places like **Shortcuts, Spotlight, Widgets**, and
more. … **even without Siri.**"* The schema is the *increment* that buys Siri execution.

Cross-reference given: *"For more details on how app schemas work, check out **my video from
WWDC24**."*

## 3.6 The Xcode schema-completeness build error — a genuinely new tooling behaviour

This is the most surprising thing in 240 and it does not appear in any doc page I know of.

> **240** — *"we adopted the `sendMessage` schema in UnicornChat. That works great. People can send
> messages with Siri. But now, let's try to build. **And we get a build error.** Xcode is telling us
> that while we adopted `sendMessage`, **we haven't adopted the related `draftMessage` schema**.
> This is important because **some Siri scenarios require more than one schema** to deliver a
> complete experience."*

> **240** — *"**This isn't just a compiler error, it's a design hint.** Xcode knows that **if your
> app can send messages with Siri, it also needs a way to draft messages, especially when
> confirmation is required.** So instead of failing silently at runtime, **the build system surfaces
> this early.**"*

And there is a fix-it:

> **240** — *"If we click into the error, **Xcode offers a fix-it**. Xcode **generates a sample
> adoption of the `draftMessage` schema**. This gives us **an intent definition, the required
> parameters and a stub implementation. All wired correctly.**"*

**Concrete facts to carry into the guide:**
- Schemas have **co-requisites** enforced at **compile time**.
- Verified co-requisite pair: **`.messages.sendMessage` ⇒ `.messages.draftMessage`.**
- The reason draft is required: **confirmation flows**. Siri drafts, shows, then sends. Without a
  draft schema there is nothing to show.
- The generated stub *"needs to run on the **main actor**"* because it *"mutates UI state"* — it
  opens the message creation view.

The generalization Apple states: *"**if a Siri experience depends on multiple schemas, Xcode will
tell you, show you what's missing, and help you generate the right remaining steps.**"*

**UNVERIFIED**: the full co-requisite graph across domains. Only the one pair was demonstrated.

## 3.7 Cross-app content transfer

Two halves, named: **on-screen awareness** (identify what "this" refers to) and **content transfer**
(move it to another app).

**[VERBATIM — Apple code sample, 240 @ 17:19]**
```swift
// Working across apps - View annotations
  
  List {
      ForEach(messages) { message in
          MessageRow(message: message)
              .appEntityIdentifier(
                  EntityIdentifier(
                      for: MessageEntity.self,
                      identifier: message.id
                  )
              )
      }
  }
```

⚠️ Note this is the **per-row** form inside a `ForEach` — precisely the pattern 343 warns about for
selection/scroll-off (§1.11). 240 is the simpler overview session; **343's collection-annotation
guidance supersedes this sample** for lists where selection matters. Worth calling out in the guide
as a "240 shows the simple form, 343 shows the correct form for lists" note.

### Export

**[VERBATIM — Apple code sample, 240 @ 18:18]**
```swift
// Working across apps - Exporting content to another app
  
  extension ContactEntity: Transferable {

      static var transferRepresentation: some TransferRepresentation {
          IntentValueRepresentation(
              exporting: \.person
          )
      }
  }
```

### Import — two mutually exclusive strategies

The decision rule, verbatim, and it is crisp:

> **240** — *"When content comes into your app, there are usually **two possibilities**. Either that
> content **refers to something that already exists**, or it **represents something entirely new**.
> **You get to decide which path your app takes. If you're matching existing content, use
> `IntentValueQuery`. If you're creating something new, use `importing` on the
> `transferRepresentation`.**"*

**[VERBATIM — Apple code sample, 240 @ 19:21]**
```swift
// Working across apps - IntentValueQuery

  struct ContactEntityQuery: IntentValueQuery {

      func values(for input: [IntentPerson]) async throws -> [ContactEntity] {
          let names = input.map(\.displayName)
          let descriptor = FetchDescriptor<Contact>()
          let contacts = try model.mainContext.fetch(descriptor)
          let matches = contacts.filter { contact in
              names.contains(where: { name in
                  contact.name.localizedStandardContains(name)
              })
          }
          return matches.map(\.entity)
      }
  }
```

**Important detail:** the input here is **`[IntentPerson]`** — an *array*. In session 343 the input
was a *scalar* `AudioSearch`. So `IntentValueQuery.values(for:)` is generic over the input type and
**that type may itself be a collection**. Do not assume scalar.

`IntentPerson` has a **`.displayName`** property (240) and is constructible from a `ContactEntity`
via a `\.person` key-path (240) and used as an attendee representation (344, §4.4).

**[VERBATIM — Apple code sample, 240 @ 20:00]**
```swift
// Working across apps - IntentValueRepresentation

  extension ContactEntity: Transferable {

      static var transferRepresentation: some TransferRepresentation {
          IntentValueRepresentation(exporting: \.person, importing: { intentPerson in                    
              let contact = Contact(importing: intentPerson)
              ContactManager.shared.contacts.append(contact)
              return contact.entity
          })
      }
  }
```

`IntentValueRepresentation(exporting:importing:)` — export via key-path, import via closure
returning the new entity.

And the framing that makes the design click:

> **240** — *"**Your app doesn't need to know what happens next. It just needs to describe its
> content accurately.**"*

> **240** — *"**Many apps use both**, depending on the intent and workflow."*

## 3.8 The testing ladder — 240's four-stage recommendation

This is a genuinely useful ordered methodology and I have not seen it written down elsewhere:

| Stage | Tool | What it validates — verbatim |
|---|---|---|
| 1 | **`AppIntentsTesting`** | *"lets you exercise your intents **entirely in isolation. No Siri involved.** … **the fastest and most reliable way to validate your business logic early in development.**"* |
| 2 | **Shortcuts app** | *"**This is where you validate the shape of your intent. Not just what it does, but how it's configured and exposed.**"* |
| 3 | **Spotlight** | *"where you validate your **content integration**, ensuring your entities are **indexed correctly, discoverable, and linkable**. This helps you **confirm that Siri can find the right data before it ever tries to act on it.**"* |
| 4 | **Siri** | *"**Natural language, entity resolution, on-screen context, and cross-app workflows.**"* |

The ordering logic is a debugging funnel: isolate logic → isolate configuration → isolate retrieval
→ then the full stack. Adopt this verbatim as the guide's testing chapter spine.

## 3.9 240's own next steps

1. *"**Model and index your entities to Spotlight** so Siri can find your content."*
2. *"**Adopt app schema domains** that match your app's core experiences."*
3. *"**Adopt `Transferable`** to enable content import and export."*
4. *"**Test early and often** using AppIntentsTesting, then Shortcuts, Spotlight, and Siri."*

Closing claim worth quoting in an intro: *"By bringing your app to Siri, you're not just adding voice
support. **You're making your app faster, more accessible, and easier to use across the system.**"*

---

# 4. WWDC26 344 — Code-along: Make your app available to Siri

**Presenter:** Justin, engineer, Swift Intelligence Frameworks team.
**Source:** `https://developer.apple.com/videos/play/wwdc2026/344/` — fetched this session.
**Transcript:** `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-344.txt`

Sample app: **CometCal**, a SwiftUI + **SwiftData** calendar app.

⚠️ **No published code-sample block.** Unlike 240/343/345/237/233, session 344's page carries no
"Code Samples" section — the code was shown on screen and narrated. Everything code-shaped below is
**[RECONSTRUCTED]** from narration. Treat accordingly.

## 4.1 Why this session matters to us despite being a code-along

344 is the only source in the set that walks the **Xcode code-snippet workflow** end to end, and it
is the only place the **`calendar` domain's schema inventory** is enumerated. It also contains the
`valueState` finding (§4.7), which is a real semantic subtlety with no equivalent in the other
sessions.

## 4.2 The Xcode code-snippet workflow

> **344** — *"I'll type **`calendar_`** in the editor. **Xcode offers every schema in the Calendar
> domain, right in autocomplete.** Since the goal is a calendar entity, I'll select
> **`calendar_calendar`**."*

> **344** — *"**The snippet fills in the structure: the `@AppEntity` macro, properties,
> `DisplayRepresentation` and query stubs.**"*

**Snippet-name convention confirmed: `<domain>_<schemaName>`, typed as a bare identifier prefix.**

Snippet names verified in 344:

| Snippet | Produces |
|---|---|
| `calendar_calendar` | `@AppEntity(schema: .calendar.calendar)` scaffold |
| `calendar_attendee` | attendee entity scaffold |
| `calendar_attendeeStatus` | `@AppEnum` with *"all the cases the schema supports"* |
| `calendar_attendeeType` | `@AppEnum` for attendee kind |
| `calendar_event` | event entity scaffold |
| `calendar_createEvent` | `@AppIntent(schema: .calendar.createEvent)` with all schema params + `perform` stub |
| `calendar_updateEvent` | update intent scaffold |

Also referenced but not snippet-named: a delete-event intent, and `system.open`.

For intents specifically: *"It scaffolds the intent with the **`@AppIntent` macro, the schema, all
the parameters the schema requires, and a `perform` stub**."*

## 4.3 `CalendarEntity` — the full build order

**[RECONSTRUCTED]** — from narration, not Apple's text:
```swift
import AppIntents

@AppEntity(schema: .calendar.calendar)
struct CalendarEntity: IndexedEntity {
    var id: UUID                       // "set the id type to UUID to match the data model"

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(
            title: "\(title)",
            image: .init(systemName: "calendar")   // "a system image of a calendar"
        )
    }

    init(_ model: CalendarModel) { /* maps CalendarModel -> entity */ }
}

extension CalendarModel {
    var entity: CalendarEntity { CalendarEntity(self) }   // convenience
}

@MainActor
struct CalendarEntityQuery: EntityQuery, EnumerableEntityQuery {
    @Dependency var calendarManager: CalendarManager

    func entities(for identifiers: [UUID]) async throws -> [CalendarEntity] { /* fetch by ID */ }
    func allEntities() async throws -> [CalendarEntity] { /* all calendars */ }
}
```

**Facts asserted in narration (these are reliable even though the code is reconstructed):**
- `IndexedEntity` conformance is what buys semantic matching: *"Conforming to `IndexedEntity` allows
  my app to **donate entities using the Spotlight index** to get the benefits of semantic
  understanding. **When an entity is donated, Siri can resolve it by name, by property, or by
  context, without requiring a custom property query.**"*
- **`@Dependency`** — *"the property wrapper is **how App Intents injects shared resources** into
  intents and queries, so **instead of creating new instances, it provides the same object I
  register once**."*
- Main-actor propagation: *"The `CalendarManager` is main-actor isolated, so I'll **also annotate
  the query struct as `@MainActor`**."*
- **`EnumerableEntityQuery`** and **why** you need it beyond `EntityQuery`: *"`EntityQuery` covers
  cases where **the system already knows an entity's ID**. But later, when **creating events, the
  system will need to know which calendars are available so Siri can offer them as options**. For
  that, I'll conform to `EnumerableEntityQuery` and add an **`allEntities`** method."*

  That is a clean, memorable rule: **`EntityQuery` = resolve by ID; `EnumerableEntityQuery` = offer
  as a choice.**

### ⚠️ The easy-to-miss step: indexing is a separate obligation

> **344** — *"There's one more piece that's easy to miss. **`IndexedEntity` defines the shape of my
> indexed content, but entities still need to be donated.**"*

**[RECONSTRUCTED]** — the `CalendarManager` side:
```swift
@MainActor
final class CalendarManager {
    private let searchableIndex: CSSearchableIndex

    init() {
        // "a CSSearchableIndex instance ... that uses a unique name for CometCal"
        self.searchableIndex = CSSearchableIndex(name: "com.example.CometCal.index")
    }

    func createCalendar(...) throws -> CalendarModel {
        // ... create ...
        try await searchableIndex.indexAppEntities([model.entity])
        return model
    }

    func updateCalendar(...) throws { try await searchableIndex.indexAppEntities([model.entity]) }

    func deleteCalendar(...) throws {
        try await searchableIndex.deleteAppEntities(identifiers: [id], entityType: CalendarEntity.self)
    }
}
```

**Verified from narration:**
- `CSSearchableIndex(name:)` initialized once in the manager's `init`, with *"a unique name"*.
- `indexAppEntities` called in **create** and **update**.
- **`deleteAppEntities`** called in **delete**, *"passing in the **entity's id and type**"*.
  (Exact parameter labels **UNVERIFIED** — narration says "id and type", not the labels.)
- The rule: *"**Anytime calendars, or any indexed entity for that matter, are changed, the index
  needs to be updated.**"*

Verification demo: create a calendar named "Lunar Orbit Log", then swipe down to Spotlight and
search for it — *"and there it is with the calendar icon and the title."*

## 4.4 `AttendeeEntity` — `TransientAppEntity` and why

This is the clearest explanation of `TransientAppEntity` in the corpus:

> **344** — *"**A transient app entity is one that represents a temporary entity that doesn't require
> a unique identifier and isn't meant to be queried.** That's the right fit here. In CometCal, **an
> attendee represents a person's *participation in a specific event*, not the person themselves.**
> The same person can attend multiple events, and **indexing each attendance separately would create
> duplicative results in Spotlight**. Since attendees are always accessed **through the event that
> holds them**, there's **no need for an independent look up path**. `TransientAppEntity` makes that
> explicit… **no query to write, no index to maintain.**"*

**The decision rule, distilled: is this thing ever the *target* of a lookup, or only ever reached
*through* a parent?** Only-through-a-parent ⇒ `TransientAppEntity`.

⚠️ Consequence, per 343 (§1.13): a `TransientAppEntity` **cannot be used with any of the three entity
annotation APIs** (notifications, Now Playing, AlarmKit) because it has no persistent identifier.
So this choice is not purely local — it forecloses system integrations for that type.

Contents named:
- a Bool for *"whether this attendance is optional"*
- **`IntentPerson`** — *"the system's standard way to represent a person with a **name and contact
  information**. This is useful when **sharing this data between apps**, like sending an attendee's
  **email address** to draft a message in the Mail app."*
- two `@AppEnum` types, from snippets: **`calendar_attendeeStatus`**, **`calendar_attendeeType`**.

### The schema-enum adoption rule — important and generalizable

> **344** — *"**The schema defines the set of possible cases, and my app adopts the ones that
> apply.**"* … *"The snippet comes with **all the cases the schema supports**. CometCal's model
> already maps directly, so no changes are needed, but **if an app uses different terminology, simply
> map the existing model to the schema's cases so Siri can recognize the shape.**"*

And a minimum: *"**The schema requires at least one case** to describe what kind of attendee this is
and since CometCal's attendees are all people, I'll add a **`person`** case."*

So schema `@AppEnum`s are **subsettable but non-empty**. You pick from a fixed vocabulary; you may
not invent cases; you must supply ≥1.

## 4.5 `EventEntity` — composition, recurrence, unions

> **344** — *"The system's search index really shines for the event entity. When someone asks **'When
> is my crew lunch?'**, Siri can search **the title**. When they ask **'What events mention
> oxygen?'**, it can search **the note content**."*

Property-handling rules, all three stated explicitly — this is the best summary anywhere of how to
deal with a large schema:

> **344** — *"The schema defines which properties are **required** and which are **optional**. The
> essentials like **`title`** or **`startDate`** are straightforward to wire up. **Optional
> properties that my app doesn't use, like `travelTime` or `virtualLocation`, can simply stay
> unset.** **Properties that aren't part of the schema but exist on the data model, like
> `isFavorite`, can also be added to the entity.**"*

Three rules: required → wire up; optional-unused → leave unset; **non-schema → you may still add
them**. That last one is important — the schema is a floor, not a ceiling.

**Composition:** *"The calendar this event belongs to is a **`CalendarEntity`**… and the attendees is
an **array of `AttendeeEntity`**. **Siri understands these relationships with App Schemas.**"*

**Recurrence:** *"It uses **Foundation's `Calendar.RecurrenceRule`** type and converts to and from
CometCal's simple frequency enum for cases like **daily, weekly, monthly or yearly**."*

**Union values in the calendar schema — two of them, with concrete member types:**

| Property | Union members |
|---|---|
| `location` | **`PlaceDescriptor`** (GeoToolbox) **or `String`** |
| alarms | **`Duration` or `Date`** |

The `location` union corroborates 345's `PlaceDescriptor`/GeoToolbox work (§2.2) — the same type is
both the calendar location union member and the Maps transfer payload. `PlaceDescriptor` is the
system's canonical "a place" currency type.

*"Like the attendee, there are also schematized enums here like the **`EventEntityStatus`**."*
*"Both enums related to events come complete from the snippets"* — the second is
**UNVERIFIED** by name; from the delete section it is plausibly an event **span** enum (§4.8).

## 4.6 `system.open` — closing the tap-through gap

A genuinely useful diagnostic story:

> **344** — *"tapping the event from my conversation with Siri **opens CometCal, but it just lands on
> the main screen. It doesn't navigate to the event** like I would expect. **Siri doesn't know how to
> open a specific event in the app yet.**"*

The fix:

> **344** — *"here's an **`OpenEventIntent`**. It's a small intent that conforms to the **`system.open`
> schema**. It **takes an `EventEntity` as its `target`** and tells the `NavigationManager` to
> navigate to that event. **The system calls this whenever someone taps an event result in Spotlight
> or Siri, or asks Siri to open one.**"*

**[RECONSTRUCTED]**
```swift
@AppIntent(schema: .system.open)
struct OpenEventIntent {
    var target: EventEntity

    @Dependency var navigation: NavigationManager

    @MainActor
    func perform() async throws -> some IntentResult {
        navigation.navigate(to: target)
        return .result()
    }
}
```

**Confirmed from narration:** the parameter is named **`target`**; the schema is **`.system.open`**;
three trigger surfaces — Spotlight result tap, Siri result tap, and *"asks Siri to open one"*.

This is a **cheap, high-value adoption** and belongs early in any guide's checklist: without it,
every Siri/Spotlight result tap dead-ends on your root screen.

## 4.7 ⚠️ `IntentParameter.valueState` — the nil-ambiguity fix

The single most valuable API detail in 344, and it has no analogue in the other sessions.

> **344** — *"there's one important subtlety with **optional parameters in update intents** worth
> calling out. For example, **when `recurrence` is nil, does that mean "don't change it" or "remove
> it"? A simple nil check doesn't tell me which case I'm dealing with.** … the `@AppIntent` macro
> **wraps each property in an `IntentParameter` which exposes a `valueState`**. This is how I tell
> the difference. **`.set` with an actual value** means a new value is provided. **`.set` with a nil
> value** means it's **explicitly cleared**. **`.unset`** means **the parameter isn't part of the
> request**."*

**Confirmed API:** `$parameter.valueState`, an enum with **`.set(T?)`** and **`.unset`**.

Three-state truth table:

| `valueState` | Meaning | Correct action |
|---|---|---|
| `.set(value)` | new value supplied | assign it |
| `.set(nil)` | **explicitly cleared** | delete/clear the field |
| `.unset` | not part of this request | **leave untouched** |

**[RECONSTRUCTED]**
```swift
switch $recurrence.valueState {
case .set(let rule?):  updates.recurrence = convert(rule)   // change it
case .set(nil):        updates.recurrence = nil             // clear it
case .unset:           break                                // don't touch it
}
```

Generalization Apple states: *"**This pattern applies to any optional parameter where clearing the
value is a meaningful action.**"*

⚠️ **This is a correctness bug generator.** Any update-style intent written with `if let x = param`
silently conflates "clear it" with "don't touch it". Every `.update*` schema in every domain is
exposed. This deserves its own callout box in the guides.

## 4.8 Create / update / delete — the general shape

> **344** — *"The general pattern is straightforward: **resolve the intent's parameters into
> something the data layer understands, perform the action, and return the result as an entity.**"*

For update: *"**most parameters are optional** since someone might only change one or two things.
**The `event` parameter is what Siri resolves; everything else is optional.**"*

For delete: *"just the **event** and an **optional `span`** for recurring events. … **Siri
automatically handles the confirmation dialog before anything is removed.**"* — and the demo shows
Siri also disambiguating: *"**makes sure to disambiguate when more than one event matches.**"*

Snippet views on results: *"By default, **Siri builds the result card from the display
representation**. Snippet views let me replace that with a custom SwiftUI view."* — add
`ShowsSnippetView` to the return type and pass the view in `.result(…)`. Design advice: *"You can get
really creative here… **but also remember to keep it simple and lightweight.**"*

## 4.9 Onscreen awareness in 344 — the two-modifier minimum

> **344** — *"**that's onscreen awareness... and it takes just two view modifiers.**"*

- List view: `.appEntityIdentifier` on the **list**, *"passing in an `EntityIdentifier` for each of
  the event entities"* — i.e. the collection form.
- Detail view: `.userActivity` **with an `EntityIdentifier`** — *"This tells the system that **one
  specific event is front and center** so Siri can resolve this event to exactly the one being
  viewed."*

Same split as 343 §1.11: collection for lists, `NSUserActivity` for the dedicated screen.
Demo utterances enabled: *"open that **third** event"*, *"email the people in **this** event"*.

## 4.10 344's claimed effort

Worth quoting as an adoption-cost datapoint: *"**Not bad for three structs and filling out a few code
snippets, right?**"* (for the entire content layer: Calendar, Attendee, Event) and *"**Seriously…
two modifiers… that's all it takes** to connect what's on screen to the app's content."*

---

# 5. WWDC26 237 — What's new in image understanding

**Presenter:** Megan Williams, **Vision framework team**.
**Source:** `https://developer.apple.com/videos/play/wwdc2026/237/` — fetched this session.
**Transcript:** `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-237.txt`

This is the session 241 pointed at for `BarcodeReaderTool`/`OCRTool`. It is the **detail source** for
image tool calling.

## 5.1 Tap-to-segment — `GenerateIterativeSegmentationRequest`

Four selection modalities named: **point, bounding box, lasso, scribble**. Plus **iterative
refinement** by adding *included* or *excluded* points.

**[VERBATIM — Apple code sample, 237 @ 4:15]**
```swift
// Generate a segmentation mask of an object with a seed point
let handler = ImageRequestHandler(image)
let request = GenerateIterativeSegmentationRequest(seed: point)
let observation = try await handler.perform(request)
let mask = observation?.pixelBuffer

// Refine the mask with a new point
request.addIncludedPoint(newPoint)
let refinedObservation = try await handler.perform(request)
```

**Confirmed API:** `ImageRequestHandler(_:)`, `GenerateIterativeSegmentationRequest(seed:)`,
`handler.perform(_:) async throws`, `observation?.pixelBuffer`, `request.addIncludedPoint(_:)`.
An exclusion counterpart is demonstrated in the demo (*"choose a point on the cup to **exclude**"*)
but its method name is **UNVERIFIED** (`addExcludedPoint` is the obvious guess — do not assert).

### Three constraints stated, all easy to get wrong

1. **Coordinates:** *"Vision uses a **normalized coordinates system with the coordinate origin in the
   lower left hand corner**. Points should be **normalized to the image width and height, with
   coordinate values between 0 and 1**."*
2. **Lasso stroke width:** *"**Thin strokes may not produce the best result. The line width should be
   at least 1% of the total image width.**"*
3. **Model download required:** *"**before you perform a segmentation request for the first time on a
   device, you'll have to download the model.** You can use the **`downloadAssets`** API to begin a
   download. And if you're not sure whether the model is downloaded or not, you can check
   **`assetStatus`** to see if the model is ready to use."*

Constraint 3 is a shipping-blocker class of issue — first-run latency and offline failure.

## 5.2 Image attachments in Foundation Models

**[VERBATIM — Apple code sample, 237 @ 6:41]**
```swift
// Generate an image caption with Foundation Models
import FoundationModels

let prompt = Prompt {
    "Generate a caption for this image"
    Attachment(image)
}
let response = try await session.respond(to: prompt)
let caption = response.content
```

`Attachment(_:)` inside the `Prompt` builder. This corroborates session 241's image-attachment
material already in the corpus.

## 5.3 Vision vs Foundation Models — the framing to steal

> **237** — *"The Foundation Models framework leverages large language models, which **can do almost
> anything you ask them**. By comparison, traditional image processing frameworks, like Vision, use
> a **fixed set** of computer vision APIs. **Vision APIs are fine tuned for specific tasks, which
> they do really well. And Vision is fast. Often fast enough to analyze video frames in real time.**"*

> **237** — *"**But you don't always have to choose** between Vision and Foundation Models to analyze
> your images. **There's a way to leverage Vision's expertise with Foundation Model's versatility
> using tool calling.**"*

That is the thesis of the whole session and the justification for the built-in tools.

## 5.4 `ImageReference` — image arguments in tool calling

New this year and it is the mechanism that makes image tools possible:

> **237** — *"**This year, tool calling supports image arguments.** … Rather than passing the whole
> image as an argument, the model would instead **pass a reference to the image**."*

**[VERBATIM — Apple code sample, 237 @ 9:55]**
```swift
// Create an image-based tool
struct PlantIdentifierTool: Tool {
    @SessionProperty(\.history) var history

    @Generable
    struct Arguments {
        var image: ImageReference
    }

    func call(arguments: Arguments) async throws -> String {
        let imageReference = arguments.image
        let transcript = Transcript(history)
        guard let imageAttachment = imageReference.resolve(in: transcript) else {
            throw AppError.imageNotFound
        }
        let image = try imageAttachment.pixelBuffer()
        return classifyPlant(image)
    }
}
```

**This is the most API-dense sample in the session. Confirmed surface:**

| Symbol | Notes |
|---|---|
| **`ImageReference`** | *"This signals to the model that the argument needs to be **a reference to an existing image from the current chat session**."* Used as a `@Generable Arguments` property type. |
| **`@SessionProperty(\.history)`** | property wrapper; `\.history` key-path. *"To access this transcript, use the **`history` session property**."* |
| **`Transcript(history)`** | constructs a `Transcript` from the session history value. |
| **`imageReference.resolve(in: transcript)`** | returns an optional image attachment. |
| **`imageAttachment.pixelBuffer()`** | `throws`; yields the `CVPixelBuffer` for analysis. |

⚠️ **Scoping rule, verbatim, and it is a real constraint:** *"**Each `imageReference` is only valid
in the context of the transcript from which it was generated.**"* You cannot stash an
`ImageReference` and resolve it later against a different session.

Note this tool's `Output` is a plain **`String`** (`call` returns `String`). That is directly
relevant to §5.6.

## 5.5 ✅ `BarcodeReaderTool` — declaration RESOLVED

Sources: session 237 transcript + Apple's published code sample for 237 + the doc page fetched via
`https://sosumi.ai/documentation/vision/barcodereadertool` and
`…/barcodereadertool/init(name:description:)`.

### Declaration and availability — VERIFIED from the doc page

```swift
struct BarcodeReaderTool
```

- **Framework:** Vision
- **Availability:** **iOS 27.0+ Beta, iPadOS 27.0+ Beta, macOS 27.0+ Beta, visionOS 27.0+ Beta,
  watchOS 27.0+ Beta**
- **Summary:** *"A tool that scans machine-readable codes in an image."*
- **Conforms To:** `Sendable`, `SendableMetatype`, **`Tool`** (`/documentation/FoundationModels/Tool`)

### Initializer — VERIFIED verbatim from the doc page

```swift
init(name: String? = nil, description: String? = nil)
```

- *"Creates a tool for decoding machine-readable codes."*
- **`name`** — *"The name of the tool as exposed to the model."* `nil` ⇒ default naming.
- **`description`** — *"A description of what the tool does, **used by the model to determine when to
  call it**."* `nil` ⇒ default description.

### Output — VERIFIED prose, not a type name

> **doc page Overview** — *"When the model encounters an image containing machine-readable codes, it
> can call this tool to decode them. **The tool returns an array of `Barcode` results, each
> containing the decoded content and the symbology type.**"*

So: **`Output` is an array of `Barcode`**, each carrying **decoded content** + **symbology type**.
The `Barcode` type is named in the doc prose (rendered as a code-span) but there is no linked
`Barcode` symbol page in the topics list I retrieved.

### Usage — VERIFIED verbatim from the doc page Overview

```swift
let barcodeTool = BarcodeReaderTool()
let session = LanguageModelSession(tools: [barcodeTool])
```

```swift
let customTool = BarcodeReaderTool(
    name: "scanQRCode",
    description: "Scan QR codes"
)
```

Doc prose for the second: *"**You can override the default name and description to customize how the
model identifies and uses the tool.**"*

### Usage from the session — VERIFIED, and it adds the `.label()` requirement

**[VERBATIM — Apple code sample, 237 @ 12:09]**
```swift
// Use Vision tools
import FoundationModels
import Vision

let session = LanguageModelSession(model: model, tools: [BarcodeReaderTool()])
let response = try await session.respond(generating: EventInfo.self) {
    "Get the date, location, and website from this flyer"
    Attachment(image)
        .label("flyer")
}
```

Two things this adds over the doc page:
1. `LanguageModelSession(model:tools:)` — the tools go on the **session**, alongside a model.
2. **`Attachment(image).label("flyer")`** — and the accompanying rule:

> **237** — *"**It's also important that you give attached images a label when you want the model to
> make an image-based tool call. This label is how the model will identify which image to pass to the
> tool.**"*

⚠️ **This is a silent-failure condition.** Unlabelled attachments + an image tool = the model has no
way to name the image in its tool call. Nothing errors. Put this in the guide as a hard requirement,
not a tip.

Also note `session.respond(generating: EventInfo.self) { … }` — guided generation and image tool
calling compose.

### The demonstrated capability gap that motivates the tool

> **237** — *"I have an event flyer here, and I'm asking the model to extract information like the
> date, location, and website registration. **Without tools enabled, the model can find the location
> and the date, but it can't read the QR code.**"* … *"**Some models struggle to read barcodes and QR
> codes.**"*

## 5.6 ✅ `OCRTool` — declaration RESOLVED

Source: `https://sosumi.ai/documentation/vision/ocrtool` and `…/ocrtool/init(name:description:)`.

### Declaration and availability — VERIFIED

```swift
struct OCRTool
```

- **Framework:** Vision
- **Availability:** **iOS 27.0+ Beta, iPadOS 27.0+ Beta, macOS 27.0+ Beta, visionOS 27.0+ Beta**
- **Summary:** *"A tool that recognizes text in an image."*
- **Conforms To:** `Sendable`, `SendableMetatype`, **`Tool`**

### ⚠️ Availability asymmetry — a real finding

**`BarcodeReaderTool` lists watchOS 27.0+. `OCRTool` does NOT list watchOS.**

I fetched both pages this session and the platform lists differ by exactly that one entry. Given
that 237's closing section is specifically about **Vision arriving on watchOS**, this is plausibly
intentional (OCR is heavier), not a doc typo — but I have not confirmed the reason. Recorded as a
**VERIFIED difference with an UNVERIFIED cause.** If our guides claim "both Vision tools are
available on all platforms", that is wrong.

### Initializer — VERIFIED verbatim

```swift
init(name: String? = nil, description: String? = nil)
```

- *"Creates a tool for recognizing text in images."*
- **`name`** — the tool's identifier as presented to the model; omitted ⇒ system default naming.
- **`description`** — explains the tool's functionality, *"which the model uses to determine
  invocation timing"*; omitted ⇒ default supplied.

Identical shape to `BarcodeReaderTool`'s initializer.

### Output — VERIFIED prose

> **doc page** — *"**the tool returns a string containing all recognized text from the image.**"*

So **`Output` is `String`** for `OCRTool`, vs **`[Barcode]`** for `BarcodeReaderTool`.

### Usage — VERIFIED verbatim from the doc page

```swift
let customTool = OCRTool(
    name: "extractText",
    description: "Extract text from documents"
)
```

Instantiated as `OCRTool()` and passed to a `LanguageModelSession`.

### Capability claim from the session

> **237** — *"There's also an **OCR tool** which is good for helping models **read really fine or
> dense text**. **It can read text in over 30 languages.**"*

**"Over 30 languages"** is a concrete, citable number. Note the *use case* framing — *fine or dense*
text — implies the base model already handles ordinary legible text; the tool is for the hard cases.

### 🟡 What is STILL a gap after all this

The brief asked for *"their actual declarations, argument schemas and output types."*

| Wanted | Status |
|---|---|
| Struct declaration | ✅ `struct BarcodeReaderTool` / `struct OCRTool` |
| Availability | ✅ iOS/iPadOS/macOS/visionOS 27.0+ Beta (+watchOS for barcode only) |
| Conformances | ✅ `Sendable`, `SendableMetatype`, `Tool` |
| Initializer + defaults | ✅ `init(name: String? = nil, description: String? = nil)` |
| **`Arguments` associated type** | ❌ **NOT PUBLISHED.** Neither doc page lists an `Arguments` type, a nested `Arguments` struct, or `call(arguments:)`. The topics list contains only the initializer. |
| **`Output` associated type (as a type name)** | 🟡 **Prose only.** `[Barcode]` and `String` are stated in English, not as declared associated types. |
| **`Barcode` type definition** | ❌ **NOT FOUND.** No linked symbol page. Its properties (content, symbology) are prose-only. |
| **Default `name` / `description` strings** | ❌ **NOT PUBLISHED.** Both docs say a default is supplied but never print it. |

**Recommendation for the guides:** downgrade the 🔴 GAP to 🟡 PARTIAL. We can now state the
declaration, availability, conformance, initializer and both output shapes with citations. We still
cannot state the argument schema. Given `PlantIdentifierTool` (§5.4) uses `@Generable struct
Arguments { var image: ImageReference }`, it is **highly likely** the built-in tools take a single
`ImageReference` argument — but that is **inference, not evidence.** Do not print it as fact.

## 5.7 Vision's tool-buildable surface, and watchOS

> **237** — *"**Vision supports over 30 different types of image analysis.**"* Named: image
> segmentation, **facial analysis, pose estimation, detection and image classification, trajectory
> analysis, object tracking**. Full list ⇒ *"Discover Swift enhancements in the Vision framework."*

**watchOS:** *"**This year, Vision is available in more places than ever.** You can even use Vision
to enhance your watchOS apps."*

**[VERBATIM — Apple code sample, 237 @ 13:54]**
```swift
// Create a crop that highlights a prominent subject
func generateImageCrop(in image: CGImage) async throws -> NormalizedRect? {
    let request = GenerateObjectnessBasedSaliencyImageRequest()
    let observation = try await request.perform(on: image)
    let prominentObjects = observation.salientObjects
    return prominentObjects.first
}
```

`GenerateObjectnessBasedSaliencyImageRequest()`, `request.perform(on:) async throws`,
`observation.salientObjects -> [NormalizedRect]`. Note the **`request.perform(on:)`** form here vs
**`handler.perform(request)`** in §5.1 — Vision offers both.

Use case: *"because the **watch screen is so small**, it's hard to see… **crop the image to feature
the main subject more prominently**."*

---

# 6. WWDC26 233 — Explore distributed inference and training with MLX

**Presenter:** Tatiana, research scientist, MLX team.
**Source:** `https://developer.apple.com/videos/play/wwdc2026/233/` — fetched this session.
**Transcript:** `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-233.txt`

This is the session 232 refers to. It resolves the third open question **in full**.

## 6.1 The four-layer stack — verbatim

Bottom to top:

1. **Interconnect** — *"machines need to be connected with a **physical link — an interconnect**."*
   Here: **Thunderbolt 5** cables.
2. **Transport** — **RDMA over Thunderbolt 5.**
   > **233** — *"**Starting in macOS 26.2**, Remote Direct Memory Access protocol, shortly **RDMA**,
   > is supported over **Thunderbolt 5**. **RDMA moves data directly from one machine's memory to
   > another's, avoiding most CPU and operating system overhead.**"*

   ⚠️ **macOS 26.2 is a hard version gate.** Write it down — it is the only OS version number in the
   session.
3. **Collective communication backend** — **JACCL.**
   > **233** — *"**JACCL is an open-source collective communication library built by Apple.** It
   > leverages RDMA over Thunderbolt and gives you **collective communication primitives for sending
   > data between machines and combining results across the group** — without managing any of the
   > low-level transport yourself. **And it's not limited to machine learning — any distributed
   > workload on Apple Silicon can be built on top of it.**"*
4. **ML framework** — **MLX**, which *"leverages JACCL for low-latency distributed communication and
   provides tools for orchestrating distributed jobs across the cluster."*

The layering rationale is stated too: RDMA *"alone… gives us **raw data movement between two machines
only**. Thus, distributed programs need something higher-level."*

## 6.2 Topology — mesh vs ring, and the cost model

The cost model, which is the reason the choice matters:

> **233** — *"communication time has two components: **latency and transfer time**. **Latency is the
> fixed cost paid for each communication operation, independent of the amount of data.** **Transfer
> time** … grows with message size and depends on the **bandwidth** of the link. **For small
> messages… latency dominates. For large messages, the trade off is opposite.**"*

| Topology | Property | Verbatim |
|---|---|---|
| **Mesh** | lowest latency | *"every machine connects directly to every other, thus **any group communication has the lowest possible latency**"* |
| **Ring** | fewer cables, higher per-link bandwidth | *"each node connects only to its two neighbors. Communication between nonadjacent nodes must **travel through intermediate machines which increases latency**. However, the ring requires **fewer cables and ports per machine, making it easier to scale to more nodes**."* |

### The ring's bandwidth trick

> **233** — *"because each node has only two connections, **we can use the extra Thunderbolt ports to
> run two or three cables per neighbor (depending on the Mac)** — thus **increasing the bandwidth per
> link and reducing transfer time**."*

### ✅ The key operational finding — mesh is strictly more flexible

> **233** — *"When machines are connected into a mesh, we have the **flexibility to route each
> communication through either a mesh topology or a ring topology**. What's nice about JACCL, **it
> automatically picks the best topology depending on the message size and communication operation —
> mesh when latency matters, ring when bandwidth matters.**"*

**Recommendation, stated as the presenter's own choice:** *"**For this flexibility, let's connect all
M3 Ultras into a mesh.**"*

So: **cable a mesh if your port count allows; JACCL will use ring routing over it when bandwidth is
what matters.** Ring cabling is the fallback for node counts a mesh can't reach.

Tensor parallelism reinforces this: *"This makes **low latency important, and that is why the mesh
topology is crucial for this case** — every machine can reach every other machine in a single hop."*

## 6.3 ✅ Enabling RDMA — the exact UI steps

> **233** — *"Open **settings** on the machine, search for **"RDMA"**, click on **"Enable RDMA over
> Thunderbolt"**, **enable RDMA, and reboot**."*

**A reboot is required.** Five steps, on **every** machine.

## 6.4 ✅ The hostfile format — RESOLVED

> **233** — *"It is a **JSON array — one entry per node**. **`"ssh"`** is the hostname used by
> `mlx.launch` to reach the machine. **`"ips"`** is the machine's IP on your **local network** used
> by **JACCL for initial coordination** between nodes. And **`"rdma"`** is a list of the **RDMA device
> names for each Thunderbolt peer connection**."*

**[VERBATIM — Apple code sample, 233 @ 8:31]**
```json
[
  {
    "ssh": "m3-ultra-0",
    "ips": ["192.168.1.10"],
    "rdma": [null, "rdma_en5", "rdma_en4", "rdma_en3"]
  },
  {
    "ssh": "m3-ultra-1",
    "ips": ["192.168.1.11"],
    "rdma": ["rdma_en5", null, "rdma_en4", "rdma_en3"]
  },
  {
    "ssh": "m3-ultra-2",
    "ips": ["192.168.1.12"],
    "rdma": ["rdma_en5", "rdma_en4", null, "rdma_en3"]
  },
  {
    "ssh": "m3-ultra-3",
    "ips": ["192.168.1.13"],
    "rdma": ["rdma_en5", "rdma_en4", "rdma_en3", null]
  }
]
```

**Structural facts worth spelling out because the example makes them implicit:**
- `"ips"` is an **array** (multiple NICs possible), `"ssh"` is a scalar string.
- **`"rdma"` is positional and self-indexed.** For node *i*, `rdma[j]` is the RDMA device on node *i*
  facing node *j* — and **`rdma[i]` is `null`** (a node has no link to itself). Every node's array
  has length = cluster size. That is the mesh encoded as an adjacency matrix of device names.
- Device names look like **`rdma_en<N>`**.

## 6.5 ✅ `mlx.distributed_config` — hostfile generation

**[VERBATIM — Apple code sample, 233 @ 8:56]**
```bash
mlx.distributed_config \
    --hosts m3-ultra-0,m3-ultra-1,m3-ultra-2,m3-ultra-3 \
    --output "m3-ultra-jaccl.json" \
    --env MLX_METAL_FAST_SYNCH=1 \
    --auto-setup \
    --backend jaccl
```

**Flags, each with its verbatim explanation:**

| Flag | Meaning |
|---|---|
| `--hosts` | comma-separated hostnames |
| `--output` | hostfile path to write |
| `--env` | *"You can also **embed environment variables in the config. They will be set automatically on every node at launch time.**"* |
| `--auto-setup` | *"**configure the Thunderbolt network automatically**"* |
| `--backend` | *"defines whether it is a **mesh or ring**: for a mesh, `--backend` is set to **`jaccl`**… for a ring, we would change it to **`jaccl-ring`**."* |

### ⚠️ `MLX_METAL_FAST_SYNCH=1` — why it is not optional

> **233** — *"Here we set **`MLX_METAL_FAST_SYNCH=1`**, which **enables faster GPU-to-CPU
> synchronization**. **It is critical for distributed tasks because computation runs on the GPU while
> communication runs on the CPU.**"*

Apple calls it *critical*, not recommended. Any distributed-MLX setup guide must include it.

### What `--auto-setup` actually does — a four-step sequence

> **233** — *"First, it **checks that all hosts are reachable over SSH**. Then it **probes each
> machine's Thunderbolt ports to discover which machines are physically connected to which — building
> a map of the topology**. Since we passed `--auto-setup`, it **disables the Thunderbolt Bridge on all
> machines** and **configures each Thunderbolt link for RDMA**. Finally, it **writes a JSON
> hostfile**."*

⚠️ **It disables Thunderbolt Bridge.** That is a destructive change to the machines' networking
config and is worth warning about.

**The escape hatch:** *"**without `--auto-setup` flag, script prints the configuration commands, so
you can review them and run yourself.**"* — recommend this for anyone who cares about their network
config.

## 6.6 ✅ `mlx.launch` — invocation RESOLVED

> **233** — *"MLX provides a **launch helper**… **You run `mlx.launch` on your MacBook and it
> orchestrates the cluster.** You give it **the executable you want to run** and a **JSON hostfile**
> describing your cluster. From there, it **SSHes into each node using hostnames from provided
> hostfile and starts the executable on every machine.**"*

**[VERBATIM — Apple code sample, 233 @ 11:04]**
```bash
# Single-device LLM inference
mlx_lm.chat --model "Qwen/Qwen3.6-27B" --max-tokens 2048

# Distributed LLM inference across the cluster
mlx.launch --hostfile "m3-ultra-jaccl.json" -- \
    /remote/path/to/mlx_lm.chat --model "Qwen/Qwen3.6-27B" --max-tokens 2048
```

**Invocation grammar: `mlx.launch --hostfile <file> -- <remote-executable-path> <its args…>`.**
The `--` separator is required; everything after it is the per-node command line.

### ⚠️ Two prerequisites stated as a warning

> **233** — *"Keep in mind that **all necessary libraries like MLX must be installed on each Mac** and
> **the executable must be accessible on all machines**."*

Hence the `/remote/path/to/mlx_lm.chat` in every sample — **you pass the path as it exists on the
nodes, not on the launcher.** That is the single most likely thing to get wrong.

Also note the launcher is *not* part of the cluster: *"From **any machine with SSH access** to the
cluster, for example **MacBook** in my case…" — the MacBook orchestrates four M3 Ultras and is not
one of the four.

## 6.7 Parallelism strategies

| Strategy | Splits by | Speeds up inference? | Communication |
|---|---|---|---|
| **Pipeline** | **depth** — *"each machine holds a **group of layers**, and data moves through the machines sequentially"* | **No** — *"**It does not speed up the inference**, because each token still has to pass through the layer groups one after another."* | *"**simple communication**: machines only exchange activations **at the boundaries between layer groups**."* |
| **Tensor** | **width** — *"each machine holds **part of every layer**, so **all machines process the same token at the same time**"* | **Yes** — *"It **improves inference speed** due to parallelized per-layer computation."* | *"**much more frequent communication, that happens at every layer and for every token**."* |

**Default:** *"**Tensor parallelism is the default sharding strategy in MLX LM.**"*
**Opt out:** *"append a flag **`--pipeline`** to the command."*
⚠️ *"**Note, that not all models support pipeline parallelism.**"*

**[VERBATIM — Apple code sample, 233 @ 15:03]**
```bash
# Tensor parallelism (default)
mlx.launch --hostfile "m3-ultra-jaccl.json" -- \
    /remote/path/to/mlx_lm.chat --model "moonshotai/Kimi-K2.6" \
                                 --max-tokens 2048

# Pipeline parallelism — append --pipeline flag
mlx.launch --hostfile "m3-ultra-jaccl.json" -- \
    /remote/path/to/mlx_lm.chat --model "moonshotai/Kimi-K2.6" \
                                 --max-tokens 2048 \
                                 --pipeline
```

## 6.8 ✅ The claimed speedups — with their hardware

**Cluster hardware, stated: 4 × M3 Ultra, meshed over Thunderbolt 5, RDMA enabled.**
Launcher: a MacBook over the local network / SSH.

| Workload | Model | Single M3 Ultra | 4 × M3 Ultra | Speedup — verbatim |
|---|---|---|---|---|
| **Inference (decode)** | Qwen 3.6, **27B** params | baseline | — | *"**The cluster generates tokens at nearly three times the rate of a single machine** for Qwen 3.6 model."* |
| **LoRA fine-tuning** | Qwen 3.5, **9B** params | **~180 tokens/sec** | **~600 tokens/sec** | *"which gives us **more than 3 times speed up** for fine-tuning"* |
| **Capacity** | Kimi 2.6, **1 trillion** params | ❌ does not fit | ✅ fits | *"Even with **8-bit quantization**, the weights alone require **about one terabyte of memory**. **That does not fit on a single M3 Ultra, but it can fit across four.**"* |

⚠️ **Caveat Apple states, and we must repeat it:** *"**The exact speedup depends on the model size and
architecture.**"* The ~3× is not a general law.

⚠️ **The 180 → 600 tok/s numbers are the only absolute figures in the session.** Everything else is a
ratio. Cite them as fine-tuning throughput on a 9B model with `mlx_lm.lora`, not as a general
benchmark.

Theoretical ceiling for data-parallel training, stated: *"**with N machines we can process data up to
N times faster.**"* — 4 machines yielded >3×, i.e. ~75-80% scaling efficiency.

## 6.9 Distributed fine-tuning — `mlx_lm.lora`

**[VERBATIM — Apple code sample, 233 @ 17:18]**
```bash
# Single-device fine-tuning
mlx_lm.lora --model "Qwen/Qwen3.5-9B" \
             --data "mlx-community/wikisql" \
             --train --batch-size 4

# Distributed fine-tuning (scale --batch-size by number of devices)
mlx.launch --hostfile "hostfile.json" -- \
    /remote/path/to/mlx_lm.lora --model "Qwen/Qwen3.5-9B" \
                                  --data "mlx-community/wikisql" \
                                  --train --batch-size 16
```

### ⚠️ The `--batch-size` scaling rule

> **233** — *"**Data sharding is handled by MLX LM** and the command is almost identical — **we scale
> `--batch-size` by the number of devices so each machine still processes the same number of samples
> per step as before.**"*

4 → 16 for 4 devices. **`--batch-size` is the GLOBAL batch, not per-device.** Forgetting to scale it
means each device sees batch/N and you change your training dynamics. This is a footgun.

Data-parallel mechanics, verbatim: *"**We replicate the model on every Mac.** Each machine receives a
**different batch of data** and **computes gradients locally**. Then we **average the gradients**, so
the model's update uses information from all batches."*

Privacy pitch worth quoting: *"Fast, efficient, and **fully private — your data never leaves your
machines**."*

## 6.10 The programmatic APIs — Python / Swift / C++

**[VERBATIM — Apple code sample, 233 @ 19:01]** — MLX LM Python, sharded load
```python
import mlx.core as mx
from mlx_lm import stream_generate
from mlx_lm.utils import sharded_load

# Initialise distributed backend
group = mx.distributed.init(strict=True, backend="jaccl")
# Define parallelism
tensor_group, pipeline_group = group, None

# Shard the model
model, tokenizer = sharded_load("moonshotai/Kimi-K2.6", pipeline_group, tensor_group)
for response in stream_generate(model, tokenizer, prompt, max_tokens=1024):
    if group.rank() == 0:
        print(response.text, end="", flush=True)
```

Note `if group.rank() == 0` — **only rank 0 prints.** Every node runs the same program; output must
be rank-gated. And `sharded_load(model, pipeline_group, tensor_group)` — pipeline group first,
tensor group second; passing `None` for pipeline gives pure tensor parallelism.

**[VERBATIM — Apple code sample, 233 @ 19:31]** — low-level layer sharding
```python
import mlx.core as mx
import mlx.nn as nn

# Initialise distributed backend
group = mx.distributed.init(strict=True, backend="jaccl")

# Define layer and shard it column-wise
layer = nn.Linear(1024, 1024)
sharded_layer = nn.layers.distributed.shard_linear(
    layer, strategy="all-to-sharded", group=group
)
data = mx.random.normal((1, 1, 1024))
output = sharded_layer(data)
mx.eval(output)
```

`nn.layers.distributed.shard_linear(layer, strategy=, group=)` with strategy
**`"all-to-sharded"`**. (Other strategy strings **UNVERIFIED**; `"sharded-to-all"` is the obvious
complement but was not shown.)

**[VERBATIM — Apple code sample, 233 @ 19:47]** — all-reduce in three languages
```python
import mlx.core as mx
world = mx.distributed.init(strict=True, backend="jaccl")
data = mx.full((4,), float(world.rank()), dtype=mx.float32)
result = mx.distributed.all_sum(data, group=world)
mx.eval(result)
```
```swift
let group = try DistributedGroup(strict: .ring)
let data = rank == 0
    ? MLXArray(converting: [1.0, 2.0, 3.0])
    : MLXArray(converting: [5.0, 6.0, 7.0])
let result = try group.allSum(data)
```
```cpp
namespace mx = mlx::core;
auto world = mx::distributed::init(/* strict */ true, "jaccl");
mx::array data = mx::full({4}, static_cast<float>(world.rank()), mx::float32);
mx::array result = mx::distributed::all_sum(data, world);
mx::eval(result);
```

**Swift API note:** `DistributedGroup(strict:)` takes an enum-ish value (`.ring` shown), and the
method is **`allSum`** (camelCase), vs `all_sum` in Python/C++. `try`-throwing in Swift.

**[VERBATIM — Apple code sample, 233 @ 20:06]** — standalone JACCL C++
```cpp
#include <jaccl/jaccl.h>
#include <iostream>

int main() {
    // Initialize JACCL group
    auto group = jaccl::init();
    std::cout << "Rank " << group->rank() << " of " << group->size() << std::endl;
    // Perform all-reduce sum
    float data[10] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f};
    float output[10];
    group->all_sum(data, output, sizeof(data), jaccl::Float32);
    std::cout << "Result: " << output[0] << std::endl;
    return 0;
}
```

**`jaccl::init()` → shared/unique ptr with `->rank()`, `->size()`, `->all_sum(in, out, byteSize,
dtype)`; `jaccl::Float32` as the dtype enum. Header `<jaccl/jaccl.h>`.**

> **233** — *"**JACCL can be built without MLX** and it provides a **C++ API** with communication
> primitives."*

That is the standalone-usability claim, restated at the end from the intro: *"any distributed
workload on Apple Silicon can be built on top of it."*

## 6.11 Loose ends 233 names but does not cover

- *"To further dive into advanced distributed features — including **custom parallelism strategies
  and training loops**, check out our **documentation**."*
- *"You can also **use MLX LM to serve models distributedly with the built-in server**."* — a
  distributed `mlx_lm.server`. **UNVERIFIED**: its invocation.
- Cross-references: WWDC25 *"Getting Started with MLX on Apple Silicon"*, WWDC25 *"Explore large
  language models on Apple Silicon with MLX"*, WWDC26 **232** *"Run local agentic AI on the Mac using
  MLX"* (already in corpus).

---

# 7. Tech Talk 111432 — Accelerate your ML workloads with the M5 and A19 GPUs

**Presenter:** Zak, manager of the **GPU Driver Performance** team at Apple.
**Source:** `https://developer.apple.com/videos/play/tech-talks/111432/` — fetched this session.
**Transcript:** `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/tech-talks-111432.txt`

⚠️ **This is a Tech Talk, not a WWDC26 session.** It predates WWDC26 (it is the M5 launch talk) and
is what session 330 means by *"the **M5 machine learning talk**"* (330:48). It is **not** listed in
`developer.apple.com/wwdc26/guides/machine-learning/`, which is why searching WWDC26 for it fails.

⚠️ **No published code-sample block.** Code was shown on screen and narrated. Symbol names below are
from narration, so they carry **transcription risk** (e.g. "metal tensor" is spoken, so
`metal::tensor` vs `MTLTensor` cannot be distinguished by ear). I have not "corrected" them.

## 7.1 The hardware claims — with their baselines

| Claim | Baseline | Verbatim |
|---|---|---|
| Image generation ~**4×** | vs **M4** | *"on the new **iPad Pro with M5**, AI image generation, apps like **Draw Things** can produce images **up to four times faster over M4** using the latest diffusion models like **Qwen-image and Flux**."* |
| Video enhancement **7.7×** | vs **M1** | *"on the new **14 inch MacBook Pro with M5**, AI video enhancement and **Topaz video is up to 7.7 times faster than on M1**."* |
| **Time to first token up to 4×** | (baseline unstated in the summary; context is M4→M5) | *"**Time to first token is up to four times faster** and **token generation is up to 25% faster**."* |
| **Matmul ("gems") 4–8×** | unstated | *"Matrix multiplication operations, often called gems, are **up to 4 to 8 times faster, depending on precision**."* |

⚠️ **The baselines differ per claim (M4 for images, M1 for video).** Any guide citing these must
carry the baseline or the number is meaningless.

Where each gain comes from — this attribution is the useful part:

> **111432** — *"the time to first token performance in the **prefill** phase is up to four times
> faster, **thanks to the neural accelerators**, and in the **decode** phase, **the increased memory
> bandwidth and larger GPU caches** in M5 speed up token generation by up to 25%."*

Named models where this was observed: **Qwen3** and **gpt-oss**.

And the zero-effort claim, stated twice: *"these speed ups come from **the new hardware, not code
changes**"* / *"performance gains **You'll see without changing a single line of code**."*

## 7.2 The compute-bound / bandwidth-bound model

This is the conceptual spine and it is well put:

> **111432** — *"For **large matrices where both inputs have lots of elements**, we have **high
> arithmetic intensity**… We call this being **compute bound**, and the performance of this scales
> with **math rates, GPU frequency and core count**. On the other end, there are cases where one of
> the matrices may be **skinny, sometimes just a single row**… We call this being **bandwidth
> bound**, and the performance of this scales with **how fast we can move data in and out of
> memory**."*

Mapped onto LLM inference:
- **Prefill** — *"processes your entire input prompt using **large matrix multiplication**… **It's
  compute bound**."* Ends at the first output token; the metric is **time to first token**.
- **Decode** — *"tokens are processed one at a time and represented by the **tall skinny matrices**…
  **the time spent generating each token is dominated by reading data from memory** to feed the
  compute units, and is thus **memory bound**."* Metric: **tokens/sec**.

Generalization: *"These performance gains are **not limited to LLMs**, but really **any workloads
that make heavy use of matmul operations, such as convolutions and running diffusion models**."*

## 7.3 Neural accelerators — where they physically are

> **111432** — *"Neural accelerators are **dedicated hardware in M5 purpose built for matrix
> multiplication**. **They're built into each shader core right alongside the other GPU pipelines**
> such as ALU, raytracing, and so on."*

Shader-core anatomy given: scheduler blocks, **ALU pipelines**, memory pipelines, **dynamic cache
memory**, and *"**The neural accelerators sit right here alongside the ALU pipelines.**"*

Two consequences drawn from that placement — both are real architectural arguments:

1. *"**This physical locality enables fast, seamless interoperation with code running on other GPU
   pipelines.**"* — i.e. you can interleave matmul and ALU work with no handoff cost. This is the
   argument for TensorOps over an off-core accelerator.
2. *"**neural accelerator capacity scales directly with core count.** So workloads that use them
   efficiently **will scale well as you move up the M5 family**."*

Other M5 GPU features listed (not ML): **2nd-generation dynamic caching**, **universal image
compression**, **3rd-generation ray tracing HW accel** for Metal RT instanced workloads.

## 7.4 The framework stack, and when to drop to TensorOps

Top to bottom, verbatim:

| Tier | Contents |
|---|---|
| Domain frameworks | **MetalFX** — *"You get the benefit of neural accelerators **automatically**"* |
| Host-side frameworks | **Metal Performance Shaders, MPSGraph, Core ML** — *"great for deploying ML models with minimal code… **great performance out of the box**"* |
| Training / research | **MLX, llama.cpp, PyTorch** — *"**already leverage neural accelerators under the hood**"* |
| Lowest level | **Metal Performance Primitives and TensorOps** — *"direct access to neural accelerators **from your metal shaders**"* |

> **111432** — *"**Most developers won't need to go this deep**, but if you're building custom ML
> kernels, optimizing a specific operation, or doing research that requires fine grained control,
> **this is what you should be using.**"*

### ⚠️ The migration directive — this is a direct instruction, not a suggestion

> **111432** — *"**And if you're already writing your own custom kernels in metal using SIMD Group
> matrix API, you should move your workloads over to adopt TensorOps instead.**"*

The three qualifying criteria, verbatim:
1. *"when you're building **custom ML kernels** and need specific optimizations **that the frameworks
   don't expose**."*
2. *"when you need to **mix matrix operations with other shader code**… so you can **combine Matmul
   with custom pre or post-processing in a single pass**."*
3. *"when you need **fine grained control over how the work is tiled, how memory is managed, and how
   threads are scheduled**."*

### Portability

> **111432** — *"**The API is portable. The same code runs across Apple's entire GPU family from M1
> to M5. On older GPUs without neural accelerators, TensorOps falls back to optimized shader
> implementations.**"*

That is a strong, citable claim: **TensorOps is not M5-only.** It is a portable API with a hardware
fast path. Important for our guides — it removes the "can I even use this" objection.

## 7.5 ✅✅ THE VERSION LADDER — the most consequential finding in this file

Verbatim, and this is the passage the brief was really after:

> **111432** — *"We introduced TensorOps at **[WWDC] 25** in the **combined metal for machine learning
> and graphics** session. … Since we introduced TensorOps, we've continued expanding the API **in iOS
> and Mac OS 26**. In **26.1**, we added **bfloat tensor support**, critical for modern ML models that
> use Bfloat16. In **26.3**, we added support for **cooperative tensors as inputs to matmul**. This
> lets you **build custom dequantization routines inside your kernel**, essential for running
> quantized models efficiently. And in **26.4**, we added **four bit and eight bit integer tensors**,
> so quantized models can fully leverage neural accelerators."*

### The ladder, tabulated

| Version | Feature added |
|---|---|
| **26.0** (WWDC25, "Combine Metal 4 machine learning and graphics", session 262) | TensorOps introduced |
| **26.1** | **bfloat** tensor support |
| **26.2** | *(nothing mentioned)* |
| **26.3** | **cooperative tensors as *inputs* to matmul** → enables custom dequantization in-kernel |
| **26.4** | **4-bit and 8-bit integer tensors** |

### What this does to our existing claims

Our `notes/CORRECTIONS-PENDING.md` C3 says, from header verification against the Xcode 26.6 SDK:
*"**Availability is 26.2**, not 27."*

**Verdict: the headline conclusion — "26.x, not 27" — is STRONGLY CORROBORATED. The specific number
26.2 is NOT corroborated, and the talk implies the real story is more granular.**

- ✅ **"Not 27" is confirmed decisively.** Every capability the M5 talk describes lands in a **26**
  point release. There is no 27 gate anywhere in this talk. Anything in our guides gated on 27 for
  TensorOps functionality is wrong.
- ⚠️ **"26.2" is the one point release the talk does NOT mention.** The talk's ladder is
  26.0 → 26.1 → 26.3 → 26.4. So a blanket "TensorOps availability is 26.2" is not what Apple
  describes. Two readings, and I cannot distinguish them from what I read:
  - (a) our "26.2" came from `@available` annotations on *specific symbols* in the shipped headers,
    and those particular symbols happen to be 26.2 while the *feature ladder* Apple narrates is
    coarser; or
  - (b) the numbers are simply different views of the same thing and one of them is imprecise.

  **Recommendation:** restate the claim as **"TensorOps ships across macOS/iOS 26 point releases —
  base at 26, bfloat at 26.1, cooperative-tensor matmul inputs at 26.3, int4/int8 tensors at 26.4 —
  and the shipped Xcode 26.6 SDK headers annotate [the relevant symbols] as 26.2."** That is
  defensible from both artifacts. Do **not** print a single blanket version.
- ✅ **The int4/int8 finding is corroborated exactly.** Our header check found *"`int8_t` and
  `metal::int4b_format` / `uint4b_format`"* present, and *"int2, fp4, fp8 and E8M0 are absent"*. The
  M5 talk announces **"four bit and eight bit integer tensors"** in 26.4 — **4 and 8 bit only.** No
  int2. No fp4. No fp8. **Two independent sources now agree on the exact dtype set.**

### ✅✅ Scale planes — the talk corroborates their non-existence, by omission AND by substitution

This is the strongest available evidence short of the headers themselves.

The M5 talk devotes a whole segment to quantization and **never once mentions a scale plane, a plane
descriptor, `blockFactors`, FP8, or E8M0.** Instead, when it reaches "how do you run quantized
models", it says:

> **111432 (26.3)** — *"we added support for **cooperative tensors as inputs to matmul**. **This lets
> you build custom dequantization routines inside your kernel**, essential for running quantized
> models efficiently."*

**That is the opposite mechanism from a scale plane.** A scale plane would mean *the tensor carries
its own scales and the hardware dequantizes*. What Apple actually shipped is: **you dequantize
yourself, into a cooperative tensor, and feed that to `matmul2d`.** That is precisely the
hand-dequantization pattern our MLX repo analysis found
(`notes/repos/mlx-tensorops-kernels.md`: *"MLX **hand-dequantises** in software into threadgroup
memory… then loads full-precision tiles into registers and cooperative tensors"*).

**Three independent sources now agree** that the scale-plane story from session 330's narration does
not correspond to shipped API:
1. MPP headers in the Xcode 26.6 SDK — zero hits for `scale`/`plane`/`fp8`/`e8m0`.
2. MLX's own kernels — hand-dequantize into cooperative tensors.
3. This M5 talk — presents in-kernel custom dequantization *as the feature*, and never mentions
   scale planes.

**Recommendation: promote C3's "scale planes do not exist" from a pending correction to a settled
finding.** Session 330's spoken "scale factors" material should be treated as describing
`matmul2d`'s ability to *accept already-dequantized cooperative tensors*, not a scale-plane
container. (330 itself is consistent with this on a close read — 330:68–75 says *"pass your
quantized tensors and TensorOps will handle dequantization for you"* **and** *"if you need to
dequantize a **custom** format… **dequantizing the data into a cooperative tensor**, which can now be
passed as an input to the `matmul2d` op."* The second half is exactly the 26.3 feature.)

## 7.6 The tiled-matmul walkthrough (the "basics" 330 refers back to)

Session 330:48 says *"We covered the basics of how to write a high performance matrix multiplication
kernel with TensorOps **in the M5 machine learning talk**."* This is that content.

**[RECONSTRUCTED — narration only, no published sample; symbol spellings are as spoken]**
```
// 1. Host side (Metal 4): declare tensors and pass them into the kernel
//    "creating three tensors with fp16 precision"
//    "The dynamic extent (dExtents) value of 2 indicates a 2D coordinate layout"

// 2. Or, inside the kernel, build a tensor from a pointer:
//    "using tensor_inline to create a tensor ... you specify the data type,
//     the coordinate extents and mark it as tensor_inline ...
//     then pass in the buffer holding your data along with the extents and strides"

// 3. Slice per threadgroup
//    "We use the slice function on our input tensors ...
//     we slice matrix A, matrix B and matrix C to get the relevant tiles
//     based on our thread group's position in the grid"

// 4. Descriptor + op
//    "First, we create a descriptor that defines the shape of our tile computation.
//     Notice here that we're using a DYNAMIC shape for the k dimension. This tells
//     TensorOps to loop over the full extent of the tensor for you, rather than a
//     static k dimension. We can also configure whether we want to transpose the
//     left or right input matrix."
//    "Next, we specify how many SIMD groups will participate ... using
//     execution_simdgroups. In this example, we're using four SIMD groups."
//    "And finally we simply call the RUN function on our extracted tensor slices."
```

**Named symbols (as spoken):** host-side `metal tensor` (likely `MTLTensor`); `tensor_inline`;
`slice(...)`; a matmul **descriptor** with a **dynamic k extent** and **transpose-left / transpose-
right** configuration; **`execution_simdgroup(s)`**; **`run(...)`**; `dExtents`.

⚠️ Cross-check against our header findings: our notes record `execution_simdgroup` /
`execution_thread` as **aliases** for `execution_simdgroups<1>` / `execution_threads<1>`, and
`matmul2d_descriptor` as taking **7 positional args** with default mode **`multiply`** (not
`multiply_accumulate`). The talk's narration is consistent with all of that at the level of detail
it gives, and adds two descriptor knobs our notes did not name: **dynamic k extent** and
**transpose flags**.

## 7.7 Cooperative tensors — the motivation and the mechanics

The motivation is a memory round-trip:

> **111432** — *"With the basic approach… you would need to **write the output tensor to device
> memory** after the Matmul completes. Then **read it back in** to apply the activation function and
> **finally write it out again**. **This double trip to memory is costly.**"*

> **111432** — *"With cooperative tensors, the output of your matrix multiplication **stays in fast
> on chip memory distributed across the threads** which are participating in your operation. You can
> then **modify these elements in place**… **Only after you've finished your modifications do you
> write the final result to device memory.**"*

Definition and layout:

> **111432** — *"It behaves just like a regular tensor, but with one key difference. **The data is
> distributed across multiple threads in the threadgroup. Each thread owns a subset of the tensor
> elements.**"* … *"**Thread zero holds the first two elements**… **thread one holds the next two
> elements**… The data is **interleaved across threads**."*

**[RECONSTRUCTED — narration only]**
```
// create the destination cooperative tensor
//   "In the template arguments, you provide the types corresponding to your input
//    tensors. The DECLTYPE keyword helps you infer these automatically. The last
//    argument specifies the data type for your destination tensor. Here we're
//    creating a HALF precision tensor."

// run the matmul into it
//   "instead of passing the regular tensor, we pass in our cooperative tensor"

// iterate + apply activation in thread memory
//   "we use GET_CAPACITY to find out how many elements this thread owns,
//    then extract each element and apply our activation function, in this case
//    a rectified linear unit (ReLU), directly"

// write out
//   "we write the results back to device memory by calling the STORE function
//    on the cooperative tensor with our output slice as the parameter"
```

**Named members:** `get_capacity()`, `store(<output slice>)`, `decltype`-based template deduction.

## 7.8 The three optimizations — this is the part with real teeth

### (1) Tile sizes

> **111432** — *"**A fixed tile size won't be optimal for all input shapes.** … **Increasing the tile
> size in the M and N directions allow better data reuse among SIMD groups within the Threadgroup**
> … On the other hand, **increasing the SIMD group tile size can reduce traffic between cache
> levels, but be careful — if you go too large, you may start spilling registers, which hurts
> performance.** **Templating your kernel so you can easily adjust tile sizes for different workloads
> is a good idea.**"*

Two knobs, opposing risks: threadgroup-level M/N tile ↑ = better reuse; SIMD-group tile ↑ = less
cache traffic **but register spill**.

### (2) ⚠️ SIMD-group drift across the K dimension — the non-obvious one

> **111432** — *"when processing the k dimension, **TensorOps will tile and loop over it for you
> automatically**, but there's a subtlety… **SIMD groups within a thread group can start to diverge in
> their progress through those K tiles.** … **they start out synchronized, but over time they drift
> apart.** **When SIMD groups drift apart, you end up with larger, more scattered cache usage
> patterns. This hurts your cache hit rates and overall performance.**"*

> **111432** — *"**The fix is to manually synchronize your SIMD groups using threadgroup barrier. To
> do this, you will want to tile the k dimension explicitly in your code so that you can insert
> barriers every few iterations.**"*

**This is a direct trade-off against the "dynamic k extent" convenience in §7.6.** Letting TensorOps
loop K for you is the easy path; doing it yourself with periodic `threadgroup_barrier()` is the fast
path. Barrier frequency is a tunable — *"Refer to the programming guide for examples of how to tune
the barrier frequency."*

### (3) Threadgroup traversal order — Morton / Hilbert

> **111432** — *"The default approach is a **linear raster order** traversal… Simple and intuitive.
> But from the perspective of your **last level cache**, **this doesn't give you great data reuse in
> the Y dimension.** A better approach is to use a **space filling curve like Morton Order or Hilbert
> order**. These traversal patterns **keep thread groups that are close in time also close in
> space**, which significantly improves **cache locality and hit rates in the last level cache**."*

## 7.9 ✅ The measured three-variant benchmark — the most citable numbers in the talk

Workload: **a single 4K × 4K matrix multiplication**, three implementations, same hardware.

| Variant | Implementation | Wall time (Metal System Trace) | Neural accelerator utilization |
|---|---|---|---|
| **v1** | classic **SIMD Group matrix** API | *"over **two seconds**"* | **0%** — *"All of this compute work is happening on the ALU, which means **the dedicated matrix hardware is sitting completely idle**"* |
| **v2** | **TensorOps** | *"**over just a half second**"* | *"**well above 50%**"* and *"**over four times faster than V1**"* |
| **v3** | TensorOps + **Morton-ordered threadgroup dispatch** | *"around **a third of a second**"* | *"**close to 100%**"* |

> **111432** — *"It's the **same 4K by 4K matrix multiplication running on the exact same hardware**.
> The difference is **almost seven times faster execution** just by understanding **how to use and
> feed neural accelerators efficiently**."*

⚠️ **The 0% utilization figure for the SIMD-group-matrix path is the headline.** It converts "you
should migrate to TensorOps" from advice into arithmetic: on M5, the old API leaves the matrix
hardware **entirely** unused. Pair it with the migration directive in §7.4.

And the diagnosis of v2, which is why v3 exists: *"**the utilization percentage tells us that the
neural accelerators could be doing more. They're waiting for data.**"* — v2 was **data-starved**, not
compute-limited. Traversal order fixed the feeding, not the math.

## 7.10 The tooling workflow

Two tools, with an explicit division of labour:

| Tool | Use | Verbatim |
|---|---|---|
| **Metal System Trace** (Instruments) | *"quick **system level** view"* | *"You can see your workload **in the context of everything else running on the system**. It's great for **rapid iteration and understanding the big picture**."* |
| **Xcode Metal debugger** | *"deep dives"* | *"**This isolates just your GPU work and removes outside system activity.**"* |

**Metal System Trace recipe, verbatim:** build (⌘B) → launch Instruments (⌘I) → choose the **Metal
System Trace** template → select the **performance limiters counter set** → record. Then expand the
**M5 Metal Device events** track; use the **track filter** to find and pin the **neural accelerator
utilization** counter.

Named tracks inside "M5 Metal Events": memory (wired footprint, alloc/dealloc), CPU-side driver
processing, and **vertex / fragment / compute** command-buffer execution.

**Metal debugger:** capture a GPU trace and replay it in Xcode. Practical tip: *"I've captured a GPU
trace of **a single K loop iteration** for each variant. **This keeps the capture small while
preserving the performance characteristics we care about.**"* Features named: **cost graph view**
inline with Metal source, **runtime statistics** (register usage, divergence, instruction-type
breakdown), **per-shader performance counters**.

The instruction-mix observation is a nice verification technique: *"in this **v1** example, which
uses SIMD group matrix, **the majority of our instruction types are math**. In this **v3** example,
**almost all of the instructions are being executed by neural accelerators**."*

## 7.11 Resources named

- **Metal Performance Primitives (MPP) Programming Guide** —
  `https://developer.apple.com/download/files/Metal-Performance-Primitives-Programming-Guide.pdf`
  Referenced **four separate times** as the place for: optimal tile sizes, barrier-frequency tuning,
  traversal-order implementation, and general TensorOps depth. **We should have this PDF locally.**
- WWDC25 **"Combine Metal 4 machine learning and graphics"** (session **262**) — the TensorOps
  introduction.
- A **companion M5 graphics/gaming tech talk**.
- The **M3 architecture tech talk** — dynamic caching and occupancy management, named as
  foundational for both M5 talks.
- From session 330's page, also: `documentation/Metal/running-inline-ml-operations-in-a-shader-with-metal-4`
  and `documentation/Metal/machine-learning-passes`.

---

# 8. Cross-cutting: contradictions and refinements

Things these seven sources change, sharpen, or confirm about what the corpus already believes.

## 8.1 "2027 releases" vs "27 releases" — NOT a contradiction

Covered in detail at §2.1. Summary: **345 says "our 2027 releases" three times; 343 and 240 say "the
27 releases"; 241 (already in corpus) says "our 2027 release".** These are the same OS family named
two ways — calendar-year branding vs version number. Independently corroborated by the `OCRTool` /
`BarcodeReaderTool` doc pages, which are the brand-new WWDC26 APIs and are annotated
**iOS 27.0+ / macOS 27.0+**.

**Action:** if a guide currently flags a discrepancy between 345's "2027" and a docs page's "27",
**close it as a non-issue** with this citation, rather than hedging.

## 8.2 `ValueRepresentation` vs `IntentValueRepresentation` — an unresolved naming collision

345 (§2.2) uses `ValueRepresentation(exporting:)`. 240 (§3.7) uses
`IntentValueRepresentation(exporting:)` and `IntentValueRepresentation(exporting:importing:)`. Both
are `TransferRepresentation`s attached via `static var transferRepresentation`. Both export an entity
as a system-understood structured type (`PlaceDescriptor` in 345; `IntentPerson` in 240).

I found no page reconciling them. **Do not assert they are the same type or that one is an alias.**
Flagged in §9.

## 8.3 343 supersedes 240 on list annotations

240 @ 17:19 shows `.appEntityIdentifier` applied **per row inside a `ForEach`**. 343 explicitly warns
that *"**Per row annotations disappear as soon as the view leaves the view hierarchy**"* and that the
collection form is needed to *"let Siri discover entities that have been **selected and scrolled off
screen**"*.

**Action:** when the guides show list annotation, show 343's `.appEntityIdentifier(forSelectionType:)`
form and mention 240's per-row form only as the simple case. Do not copy 240's sample into a
"recommended" position.

## 8.4 `TransientAppEntity` has a system-integration cost

344 §4.4 gives the clean rule for choosing `TransientAppEntity`. 343 §1.13 states that transient
entities **cannot be used with notification, Now Playing, or AlarmKit entity annotations** because
they lack persistent identifiers. Neither session mentions the other's point. **These need to be
presented together** or a reader will pick `TransientAppEntity` for good local reasons and silently
lose three system integrations.

## 8.5 `.system.searchInApp` is a RENAME, not a new schema

§1.9. The transcript says the iOS 17 `.system` search schema *"is now named `.system.searchInApp`"*.
`StringSearchCriteria`'s own doc page confirms the payload type is an **iOS 17.2** type. So the
migration story for anyone on the old `.system.search` is **rename the schema reference**, not
"rewrite against a new API". That is a materially different and much cheaper migration than our
notes currently imply, and it also explains why the domain doc page still lists `search` as
deprecated alongside `open`.

## 8.6 TensorOps versioning — see §7.5

The single most consequential correction in this file. Short form:
- ✅ **"Not 27"** — confirmed decisively; the entire M5 talk lives in **26.x**.
- ⚠️ **A blanket "26.2" is not what Apple narrates.** The narrated ladder is 26.0 / 26.1 / 26.3 /
  26.4, with **26.2 never mentioned**.
- ✅ **int4 + int8 only** (26.4) — matches our header finding exactly; **no int2, no fp4, no fp8**.

## 8.7 Scale planes — promote to settled

§7.5. Third independent source agreeing they do not exist, and — more usefully — the M5 talk
identifies **what shipped instead**: cooperative tensors as `matmul2d` *inputs* (26.3), which is the
in-kernel hand-dequantization path MLX actually uses. This gives the guides a positive story to tell
instead of just a negative correction.

## 8.8 New corroboration for `mlx.launch` / macOS 26.2 RDMA

Session 232 (in corpus) referenced this material; 233 now supplies it. Note the **macOS 26.2** gate
for RDMA over Thunderbolt 5 (§6.1) — that is a *different* 26.2 from the TensorOps one and the two
should not be conflated in the guides. One is a **transport** availability; the other is an
**MPP symbol** availability.

## 8.9 New API names introduced by these seven sources

Consolidated list of symbols that appear in these sessions and should be checked against whatever
inventory the guides maintain. All are attested in a page I read this session.

**App Intents — entities:** `OwnershipProvidingEntity`, `EntityOwnership` (`.shared`, `.public`,
`.unknown`), `IndexedEntityQuery`, `SyncableEntity`, `SyncableEntityIdentifier<Local,Stable>`,
`EntityCollection<E>` (`.identifiers`), `RelevantEntities.shared`
(`updateEntities(_:for:)`, `removeEntities(_:from:)`, `removeAllEntities(for:)`,
`removeAllEntities()`), `AppEntityContext` (e.g. `.audio(.workout(activityType:))`),
`EnumerableEntityQuery` (`allEntities()`), `TransientAppEntity`, `@Property(indexingKey:)`
(`\.textContent`).

**App Intents — intents/parameters:** `LongRunningIntent`, `CancellableIntent` (`onCancel`),
`ProgressReportingIntent`, `performBackgroundTask(_:onCancel:)`, `ExecutionTargets`
(`.main`, `.appIntentsExtension`, `.widgetKitExtension`), `allowedExecutionTargets`,
`IntentParameter.valueState` (`.set`, `.unset`), `@UnionValue` (+ `typeDisplayRepresentation`,
`caseDisplayRepresentations`, `Cases`), `Duration` / `PersonNameComponents` as native
`@Parameter` types, `$param.requestValue(_:)`.

**App Intents — transfer/queries:** `ValueRepresentation(exporting:)`,
`IntentValueRepresentation(exporting:importing:)`, `IntentValueQuery.values(for:)`,
`EntityStringQuery.entities(matching:)`, `AudioSearch` (`.criteria`: `.searchQuery`, `.unspecified`,
`.url`), `IntentPerson` (`.displayName`), `PlaceDescriptor(representations:commonName:)` +
`.coordinate(_:)` (GeoToolbox), `StringSearchCriteria` (`.term`).

**App Intents — presentation/annotation:** `DisplayRepresentation(title:subtitle:image:)`,
`DisplayRepresentation.Components` (`.text`),
`displayRepresentations(for:requestedComponents:)`, `ShowsSnippetView`, `ProvidesDialog`,
`IntentDialog(full:supporting:)`, `EntityIdentifier(for:identifier:)`,
`NSUserActivity.appEntityIdentifier`, `.appEntityIdentifier(_:)`,
`.appEntityIdentifier(forSelectionType:_:)`, `AppEntityAnnotatable`,
`UICollectionViewAppIntentsDataSource`, `appEntityUIElementProvider`,
`UNMutableNotificationContent.appEntityIdentifiers`, `MusicContent.appEntityIdentifiers`,
`MediaSessionRepresentable`, `AlarmManager.AlarmConfiguration.alarm(…appEntityIdentifier:…)`,
`IntentDonationManager.shared.donate(intent:result:)`.

**Schemas named:** `.system.searchInApp`, `.system.open`, `.audio.addToPlaylist`, `.audio.song`,
`.clock.createTimer`, `.calendar.event`, `.calendar.calendar`, `.calendar.createEvent`,
`.calendar.updateEvent`, `.messages.message`, `.messages.sendMessage`, `.messages.draftMessage`,
`.audio.playAudio` (referenced as `PlayAudioIntent`), photos schema (unnamed).

**Vision / FM:** `BarcodeReaderTool`, `OCRTool`, `ImageReference`, `@SessionProperty(\.history)`,
`Transcript(_:)`, `imageReference.resolve(in:)`, `imageAttachment.pixelBuffer()`,
`Attachment(_:).label(_:)`, `GenerateIterativeSegmentationRequest(seed:)`,
`request.addIncludedPoint(_:)`, `ImageRequestHandler`, `downloadAssets`, `assetStatus`,
`GenerateObjectnessBasedSaliencyImageRequest`, `observation.salientObjects`, `NormalizedRect`.

**MLX / JACCL:** `mlx.launch --hostfile … --`, `mlx.distributed_config` (`--hosts`, `--output`,
`--env`, `--auto-setup`, `--backend jaccl|jaccl-ring`), `MLX_METAL_FAST_SYNCH`,
`mlx_lm.chat`, `mlx_lm.lora`, `--pipeline`, `mx.distributed.init(strict=,backend=)`,
`mx.distributed.all_sum`, `mlx_lm.utils.sharded_load`,
`nn.layers.distributed.shard_linear(strategy=,group=)`, `DistributedGroup(strict:)` /
`allSum` (Swift), `jaccl::init()` / `all_sum` / `jaccl::Float32` (C++).

**Metal / TensorOps (spoken, spelling unverified):** `tensor_inline`, `slice`,
`execution_simdgroup(s)`, `run`, cooperative tensor `get_capacity` / `store`, `dExtents`,
dynamic-k descriptor extent, transpose-left/right descriptor flags, `threadgroup_barrier`,
neural-accelerator-utilization GPU counter.

---

# 9. Residual gaps

Honest list of what is still unknown after this pass. Each is phrased as something a future agent
could go and check.

## Blocking / high value

1. **`BarcodeReaderTool.Arguments` and `OCRTool.Arguments`.** Not published on either doc page.
   The topics list contains only `init(name:description:)`. **Next step:** dump the actual
   `Vision` module interface from the Xcode 27 SDK (`swift-api-digester` or
   `.swiftinterface` in the SDK) — the same technique that resolved the MPP header questions. Do not
   infer from `PlantIdentifierTool`.
2. **The `Barcode` type.** Named only in doc prose. Properties (decoded content, symbology) are
   described in English. **Next step:** same SDK dump; also check whether it is
   `Vision.BarcodeObservation` or a new tool-specific type.
3. **Default `name` / `description` strings for both Vision tools.** Both docs say a default exists;
   neither prints it. These matter because they are what the model actually sees.
4. **The TensorOps 26.2 vs 26.1/26.3/26.4 reconciliation (§7.5).** Needs a targeted re-read of the
   `@available` annotations in the MPP headers, recording *which symbol* carries which version,
   rather than a single blanket number.
5. **`ValueRepresentation` vs `IntentValueRepresentation` (§8.2).** Two names, one apparent role.

## Medium

6. **`.system.searchInApp` has no `/documentation/` page I could find.** Confirmed by two independent
   renderings on session 343's page, but not by a symbol page. `sosumi.ai/documentation/appintents/
   assistantschema/systemintent` returned 404. **Next step:** try
   `/documentation/appintents/assistantschemas` and the App Intents "app schema domains" index.
7. **`AppEntityContext`'s full domain/situation inventory.** Only
   `.audio(.workout(activityType: .running))` was shown.
8. **`DisplayRepresentation.Components` cases.** Only `.text` seen (and it is the default).
9. **The schema co-requisite graph** (§3.6). Only `sendMessage ⇒ draftMessage` demonstrated.
10. **`AudioSearch.criteria`'s full case list.** Three seen; docs said to check for more.
11. **The full list of newly-native `@Parameter` types** (§2.6) — "and more" was not enumerated.
12. **The GPU-access entitlement name** for `LongRunningIntent` background GPU (§2.8), and which
    devices are "supported devices".
13. **`CancellableIntent`'s cancellation-`reason` type.**
14. **The exclusion counterpart to `addIncludedPoint`** in `GenerateIterativeSegmentationRequest`.
15. **Which App Intents domains get semantic (vs lexical) Spotlight search** — 343 says it is
    domain-dependent but does not say which.

## Low / nice to have

16. **`shard_linear` strategy strings** beyond `"all-to-sharded"`.
17. **Distributed `mlx_lm.server` invocation** (233 mentions it exists).
18. **Session number for "Validate your App Intents adoption with AppIntentsTesting"** and for
    "Secure your app: Mitigate risks to agentic features" — both cross-referenced by these sessions,
    neither is in the ML-track guide index.
19. **The MPP Programming Guide PDF** — referenced four times by the M5 talk; we should mirror it
    locally at `https://developer.apple.com/download/files/Metal-Performance-Primitives-Programming-Guide.pdf`.
20. **The `Barcode`/`OCRTool` watchOS asymmetry cause** (§5.6) — verified as a fact, unverified as to
    why.
21. **Session 344 has no published code samples**, so every code block in §4 is reconstructed. If
    the CometCal sample project is downloadable, harvesting the real source would upgrade all of §4
    from RECONSTRUCTED to VERBATIM in one step. Same for CosmoTunes/UnicornChat (343, 240) and the
    Landmarks travel tracker (345).

---

*End of `missing-sessions.md`.*
