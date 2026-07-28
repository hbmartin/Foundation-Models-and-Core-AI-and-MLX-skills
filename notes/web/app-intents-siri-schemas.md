# App Intents, App Schema Domains, and Siri / Apple Intelligence On-Screen Awareness
## 2026 Apple platforms (iOS/macOS/watchOS/visionOS 27, WWDC26)

> **Provenance discipline.** This landscape postdates the author model's training data.
> Everything below is grounded in a page fetched during this research session.
> Apple documentation was read through the **sosumi.ai** markdown mirror
> (`https://developer.apple.com/documentation/X` -> `https://sosumi.ai/documentation/X`),
> which returns AI-readable markdown of the same canonical docs.
> Items I could not confirm from a fetched page are tagged **UNVERIFIED**.

---

## Table of contents

1. Source inventory (what worked, what failed)
2. The big picture: three separate systems people conflate
3. App schema domains — complete enumeration
   - 3.1 Domain index and taxonomy
   - 3.2 Primary domains (Audio, Calendar, Camera, Clock, Files, Mail, Maps, Messages, Notes, Phone, Photos, Reminders, System/in-app search)
   - 3.3 Single-purpose domains (Assistant, Visual Intelligence)
   - 3.4 Shortcuts-specific domains (Books, Browser, Journaling, Presentation, Reader, Spreadsheet, Whiteboard, Word processor)
   - 3.5 App schema base types
4. The schema macro system: `@AppIntent(schema:)`, `@AppEntity(schema:)`, `@AppEnum(schema:)`
5. On-screen awareness / semantic content — the actual recipe
6. Core App Intents symbol graph (AppIntent, AppEntity, EntityQuery, IndexedEntity, ...)
7. Spotlight / `IndexedEntity` / `CSSearchableItem` integration
8. Snippets and `SnippetIntent`
9. What changed in the 2026 release
10. WWDC26 sessions
11. Developer forum evidence — the pain, and Apple's answers
12. Connection to Foundation Models
13. Known limitations and error behaviors
14. Open questions / UNVERIFIED
15. Verdict: how many guides does this justify?

---

## 1. Source inventory

### Worked (fetched successfully this session)

| URL | What it gave |
|---|---|
| `https://sosumi.ai/documentation/appintents/` | Framework landing page + full topic taxonomy |
| `https://sosumi.ai/documentation/appintents/app-schema-domains` | **The domain index** — 23 domains in 3 tiers, + the three macros |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-mail` | 12 intents, 5 entities |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-files` | 5 intents, 1 entity |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-photos` | 28 intents, 3 entities, 4 enums |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-camera` | 5 intents, 3 enums |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-browser` | 13 intents, 5 entities, 1 enum |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-reader` | 9 intents, 2 entities, 1 enum |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-journaling` | 5 intents, 1 entity |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-books` | 9 intents, 3 entities, 12 enums |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-whiteboard` | 7 intents, 2 entities, 2 enums |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-assistant` | 1 intent (`activate`), Japan-only |
| `https://sosumi.ai/documentation/appintents/app-schema-domain-system-and-in-app-search` | 2 intents (`open`, `search`) |
| `https://developer.apple.com/forums/thread/838329` | **The single most valuable source in this pass.** 4 replies / 246 views. Contains the working on-screen hand-off recipe AND a DTS engineer response. |
| `https://developer.apple.com/forums/thread/837249` | 0 replies / 205 views. The "onscreen awareness can't understand an AppEntity without a schema" complaint — unanswered by Apple. |

Additional domains, core symbol pages, on-screen-awareness articles, updates pages and
WWDC26 session pages are inventoried in later sections with their own pass/fail notes.

### Local corpus files consulted

- `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-and-ai-topic-apple-intelligence.txt`
- `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-topic-general.txt`
- `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-and-ai-foundation-models.txt`

These are RSS dumps with **truncated bodies and, critically, no replies**. The replies are
where Apple staff answers live. Every high-value thread therefore had to be re-fetched from
`developer.apple.com/forums/thread/<id>` directly. This is a general lesson for the corpus:
**the RSS captures systematically omit the authoritative half of every thread.**

---

## 2. The big picture: three separate systems people conflate

A large share of the developer confusion in the forum cluster comes from treating these as
one feature. They are three distinct mechanisms with different requirements and different
degrees of openness:

**(A) App Shortcuts / voice invocation of your own intents.**
Fully open. Any `AppIntent` you write, exposed via `AppShortcutsProvider`, is invocable by
voice. The cost is that the user generally has to name your app ("How far have I traveled in
<app>?"). No schema required. This is the fallback every blocked developer lands on — and
thread 837249 explicitly describes arriving there and finding it unnatural.

**(B) App schema domains — "Siri, do this thing" without naming the app.**
Restricted. To let Siri route a *generic, un-app-qualified* request to your app, your intent
or entity must conform to one of Apple's predefined schemas via `@AppIntent(schema:)` /
`@AppEntity(schema:)`. The schema fixes the parameter list and semantics so the system knows
what your type *means*. There are 23 domains (Section 3). If your app's concept isn't in the
list, there is no supported way in.

**(C) On-screen awareness — "this".**
Restricted differently, and this is the least-documented and most-complained-about tier.
Evidence from thread 838329 (Section 5 and 11) indicates the system has two *separate* paths:
a screenshot/OCR path that runs for descriptive requests, and an entity-resolution path that
runs for hand-off requests — and the entity path in practice only resolved for a schema-typed
entity, not for a plain custom `AppEntity`.

The practical rule that falls out of the evidence: **discoverability is open, actionability is
whitelisted.** Siri can *see* your custom entity; it will not reliably *act* on it or move it
across an app boundary unless it is schema-typed.

---

## 3. App schema domains — complete enumeration

Source of the index: `https://sosumi.ai/documentation/appintents/app-schema-domains`.
Each domain below was fetched individually at
`https://sosumi.ai/documentation/appintents/app-schema-domain-<name>`.

**How to read this.** A "schema" is a predefined shape Apple has blessed. You adopt one by
attaching a macro to your own type — `@AppIntent(schema: .mail.sendDraft)`,
`@AppEntity(schema: .files.file)`, `@AppEnum(schema: .photos.filterType)`. The macro pins the
parameter names, types and semantics so the system knows what your type *means* without having
to guess. Symbol paths follow `AppSchema.<Domain><Kind>.<name>`, e.g.
`AppSchema.MailIntent.sendDraft`, documented at
`/documentation/appintents/appschema/mailintent/senddraft`.

**The schema surface is closed.** There is no mechanism to define your own domain or to
register a custom schema. If your app's core concept has no schema, the schema-based route is
unavailable to you — this is the structural fact behind the entire forum cluster.

### 3.1 Domain index and taxonomy

The docs group the 23 domains into three tiers, and **the tier determines where the schema is
usable** — this distinction is easy to miss and matters enormously:

| Tier | Domains | Reach |
|---|---|---|
| **Primary** (13) | audio, calendar, camera, clock, files, mail, maps, messages, notes, phone, photos, reminders, system | Apple Intelligence + Siri + Shortcuts |
| **Single-purpose** (2) | assistant, visualIntelligence | One specific system surface each |
| **Shortcuts-specific** (8) | books, browser, journaling, presentation, reader, spreadsheet, whiteboard, wordProcessor | **Shortcuts app only** — per the docs' own grouping |

> **This is the most under-appreciated fact in the whole area.** A developer who adopts, say,
> `.wordProcessor.createPage` expecting Siri to route natural-language requests to it is
> adopting a *Shortcuts-tier* schema. The doc taxonomy places these outside the Apple
> Intelligence/Siri tier. **UNVERIFIED**: I have the three-tier grouping and its labels from
> the index page, but I did not find a page stating in prose exactly what capability each tier
> confers. Treat the reach column as inference from the taxonomy labels, not a quoted claim.

### 3.2 Primary domains

#### `.audio` — 7 intents, 18 entities, 6 enums (largest entity surface of any domain)

*Intents:* `playAudio`, `addToLibrary`, `addToPlaylist`, `createStation`, `recognizeAudio`,
`updateAudioAffinity`, `warmupAudioQueue`

*Entities:* `album`, `algorithmicRadioStation`, `ambientSound`, `artist`, `audiobook`,
`classicalMusicRecording`, `liveRadioStation`, `newsBrief`, `newsProvider`, `playlist`,
`podcastCollection`, `podcastEpisode`, `podcastShow`, `radioShow`, `radioShowEpisode`, `song`,
`songCollection`, `warmupAudioQueueResult`

*Enums:* `activity`, `affinityState`, `appViewIdentifier`, `invocationSource`,
`playbackAttributes`, `queueInsertionLocation`

Note `warmupAudioQueue` / `warmupAudioQueueResult` — a latency-optimization pair with no
analogue in other domains. Audio is clearly the most heavily invested domain, presumably
because "play X" is the highest-volume Siri request category.

#### `.calendar` — 3 intents, 3 entities, 4 enums

*Intents:* `createEvent`, `deleteEvent`, `updateEvent`
*Entities:* `attendee`, `calendar`, `event`
*Enums:* `attendeeStatus`, `attendeeType`, `eventSpan`, `eventStatus`

Note the absence of any *query/search* intent. Reading the calendar is not a schema action.

#### `.camera` — 5 intents, 3 enums, **0 entities**

*Intents:* `openInCaptureMode`, `setDevice`, `startCapture`, `stopCapture`, `switchDevice`
*Enums:* `captureDevice`, `captureDuration`, `captureMode`

A pure control surface — nothing to reference, only things to do.

#### `.clock` — 10 intents, 2 entities, 2 enums

*Intents:* `createAlarm`, `updateAlarm`, `snoozeAlarm`, `dismissAlarm`, `deleteAlarm`,
`createTimer`, `updateTimer`, `pauseTimer`, `resumeTimer`, `cancelTimer`
*Entities:* `alarm`, `timer`
*Enums:* `alarmTriggerState`, `timerState`

#### `.files` — 5 intents, 1 entity — **the load-bearing domain for on-screen hand-off**

*Intents:* `createFolder`, `deleteFiles`, `moveFiles`, `openFile`, `renameFile`
*Entities:* `file`

Tiny domain, outsized importance. `.files.file` is the schema that thread 838329 found to be
the *only* working route for handing an on-screen item to another app (Section 5). Its
associated identifier type `FileEntityIdentifier` and the `FileRepresentation` transfer
representation are the mechanism. Note the doc page for the domain does **not** itself mention
`FileEntityIdentifier` or `FileRepresentation` — that linkage came from the forum thread, which
is a documentation gap worth flagging.

#### `.mail` — 12 intents, 5 entities

*Intents:* `createDraft`, `updateDraft`, `saveDraft`, `openDraft`, `deleteDraft`, `sendDraft`,
`openMessage`, `replyMail`, `forwardMail`, `updateMail`, `archiveMail`, `deleteMail`
*Entities:* `account`, `draft`, `mailbox`, `message`, `thread`

A clean full-CRUD design. Good reference model for what "complete" schema coverage looks like.

#### `.maps` — 6 intents, 6 entities, 7 enums

*Intents:* `startNavigation`, `stopNavigation`, `addNavigationWaypoints`, `shareETA`,
`stopShareETA`, `reportIncident`
*Entities:* `currentLocation`, `navigationSession`, `operatingHours`, `operatingTimeRange`,
`place`, `rating`
*Enums:* `amenity`, `incident`, `navigationPreferences`, `operatingStatus`, `priceRange`,
`ratingDescriptor`, `transportType`

**Directly relevant to forum thread 837249** (the hiking/cycling app). `.maps` has
`navigationSession` as an entity and `addNavigationWaypoints` as an intent — but there is **no
schema for querying progress metrics** (distance covered, elevation gain remaining, ETA to next
waypoint). The developer's use case falls in the gap between "start navigation" and "no way to
ask about it." That is precisely why their custom `AppEntity` had nowhere to attach.

#### `.messages` — 5 intents, 4 entities, 5 enums

*Intents:* `draftMessage`, `sendMessage`, `editSentMessage`, `unsendMessage`,
`setMessageReadStatus`
*Entities:* `conversation`, `customAttachment`, `message`, `messagePerson`
*Enums:* `conversationAttribute`, `customReaction`, `messageAttribute`, `messageEffect`,
`messageType`

`customAttachment` is the entity that makes "send this to <contact>" able to carry a payload.

#### `.notes` — 2 intents, 3 entities

*Intents:* `createNote`, `updateNote`
*Entities:* `account`, `folder`, `note`

Doc text: *"Make your note-taking app's actions available to Apple Intelligence and Siri by
adopting schemas for common note actions."* Note there is no `deleteNote` and no search.

#### `.phone` — 1 intent, 1 entity, 1 enum

*Intents:* `startCall`
*Entities:* `phonePerson`
*Enums:* `audioVisualMode`

Smallest domain. Doc text: *"Make your phone app's actions available to Apple Intelligence and
Siri by adopting schemas for calling actions."*

#### `.photos` — 28 intents, 3 entities, 4 enums (largest intent surface of any domain)

*Intents:* `addAssetsToAlbum`, `cleanupPhoto`, `copyEdits`, `createAlbum`, `createAssets`,
`crop`, `deleteAlbum`, `deleteAssets`, `duplicateAssets`, `editAsset`, `openAlbum`,
`openAsset`, `pasteEdits`, `postToSharedAlbum`, `removeAssetsFromAlbum`, `setDepth`,
`setExposure`, `setFilter`, `setRotation`, `setSaturation`, `setWarmth`, `straighten`,
`toggleDepth`, `toggleSuggestedEdits`, `updateAlbum`, `updateAsset`, `updateRecognizedPerson`,
`search` (deprecated)
*Entities:* `album`, `asset`, `recognizedPerson`
*Enums:* `albumType`, `assetType`, `filterType`, `rotationDirection`

The editing verbs (`setExposure`, `setWarmth`, `straighten`, ...) show the intended granularity:
schemas can be very fine-grained *within* a blessed domain.

#### `.reminders` — 8 intents, 5 entities, 2 enums

*Intents:* `createList`, `createReminder`, `createSection`, `deleteReminders`, `updateGroup`,
`updateList`, `updateReminder`, `updateSection`
*Entities:* `group`, `list`, `locationTrigger`, `reminder`, `section`
*Enums:* `listType`, `locationTriggerEvent`

#### `.system` — "System and in-app search" — 2 intents

*Intents:* `open`, `search` (**deprecated**)

Doc text: the `.system` domain provides *"a structured representation for common search actions
and content"* applicable to any app category that handles searching or opening content.

**The deprecation of `.system.search` is significant.** This was the generic, category-agnostic
"let Siri search inside my app" escape hatch. Its deprecation — alongside deprecated `search`
in `.browser`, `.books` and `.journaling` — points to search being deliberately migrated to
**Spotlight / `IndexedEntity`** (Section 7) rather than remaining an intent-schema action. See
Section 9.

Implementation hint from the doc: *"Xcode generates a template implementation when you type
`system_` and select a schema from the suggestions list."* The `<domain>_` prefix trigger
appears to be the general Xcode discovery mechanism for schema templates.

### 3.3 Single-purpose domains

#### `.assistant` — 1 intent, **Japan only**

*Intents:* `activate`

Doc text: this schema *"registers your app as a side button action on iPhone. This schema is
available only in Japan."* Related guide: "Launching voice-based conversational app from the
side button of iPhone."

Worth calling out because the name `.assistant` invites the assumption that this is the
general-purpose "make my app an assistant" hook. It is not. It is a regional side-button
registration with exactly one action.

#### `.visualIntelligence` — 1 intent

*Intents:* `semanticContentSearch`

Doc text: the domain *"connects your app to the camera control"*, letting users *"point the
camera at relevant content"* and get results from your app.

Adoption requires three things:
1. Apply the `semanticContentSearch` schema.
2. Implement an **`IntentValueQuery`** that receives Visual Intelligence types.
3. Match captured camera/screenshot content to your app entities and return results.

Note `IntentValueQuery` — a distinct query protocol from `EntityQuery`, and the one place in
the schema system where the app receives *system-captured visual content* as input. This is the
closest existing analogue to what thread 838329's author wanted, but it is scoped to the camera
control surface, not to arbitrary on-screen content.

### 3.4 Shortcuts-specific domains

Per the index page's own grouping, these eight are **Shortcuts-specific** rather than
Apple Intelligence/Siri-tier.

#### `.books` — 9 intents, 3 entities, 12 enums

*Intents:* `navigatePage`, `openBook`, `updateCharacterSpacing`, `updateFontSize`,
`updateLineSpacing`, `updateSettings`, `updateWordSpacing`, `playAudiobook` (**deprecated**),
`search` (**deprecated**)
*Entities:* `audiobook`, `book`, `settings`
*Enums:* `contentType`, `font`, `fontSize`, `navigationDirection`, `pageNavigationSetting`,
`relativeCharacterSpacingChange`, `relativeFontChange`, `relativeLineSpacingChange`,
`relativeWordSpacingChange`, `theme`

`playAudiobook` deprecated presumably in favour of `.audio.playAudio` + `.audio.audiobook`.

#### `.browser` — 13 intents, 5 entities, 1 enum

*Intents:* `bookmarkTab`, `bookmarkURL`, `clearHistory`, `closeTabs`, `closeWindows`,
`createTab`, `createWindow`, `deleteBookmarks`, `findOnPage`, `openBookmark`, `openURLInTab`,
`switchTab`, `search` (**deprecated**)
*Entities:* `bookmark`, `readingListItem`, `tab`, `tabGroup`, `window`
*Enums:* `clearHistoryTimeFrame`

#### `.journal` — 5 intents, 1 entity

*Intents:* `createAudioEntry`, `createEntry`, `deleteEntry`, `updateEntry`,
`search` (**deprecated**)
*Entities:* `entry`

Note the symbol is `AppSchema.JournalIntent` (singular "Journal"), while the domain page is
titled "Journaling" and lives at `app-schema-domain-journaling`. Mind the mismatch.

#### `.presentation` — 14 intents, 3 entities

*Intents:* `addAudioToSlide`, `addCommentToSlide`, `addImageToSlide`, `addTextBoxToSlide`,
`addWebVideoToSlide`, `create`, `createSlide`, `deleteSlide`, `open`, `openSlide`,
`setSlideTitle`, `startPlayback`, `stopPlayback`, `update`
*Entities:* `document`, `slide`, `template`

#### `.reader` — 9 intents, 2 entities, 1 enum

*Intents:* `deletePages`, `enhanceDocuments`, `insertPages`, `openDocument`, `openPage`,
`resizeDocuments`, `rotateDocuments`, `rotatePages`, `searchDocuments`
*Entities:* `document`, `page`
*Enums:* `documentKind`

Note `.reader` keeps a live `searchDocuments` while other domains' generic `search` was
deprecated — the surviving search verbs are the *domain-specific* ones.

#### `.spreadsheet` — 14 intents, 3 entities

*Intents:* `addAudioToSheet`, `addCommentToSheet`, `addImageToSheet`, `addTextBoxToSheet`,
`addVideoToSheet`, `addWebVideoToSheet`, `create`, `createSheet`, `delete`, `deleteSheet`,
`open`, `openSheet`, `update`, `updateSheet`
*Entities:* `document`, `sheet`, `template`

#### `.whiteboard` — 7 intents, 2 entities, 2 enums

*Intents:* `createBoard`, `createItem`, `deleteBoard`, `deleteItem`, `openBoard`, `updateBoard`,
`updateItem`
*Entities:* `board`, `item`
*Enums:* `color`, `itemType`

#### `.wordProcessor` — 9 intents, 3 entities

*Intents:* `addAudioToPage`, `addImageToPage`, `addTextBoxToPage`, `addVideoToPage`,
`addWebVideoToPage`, `create`, `createPage`, `open`, `openPage`
*Entities:* `document`, `page`, `template`

The three productivity domains (`.presentation`, `.spreadsheet`, `.wordProcessor`) are
near-isomorphic: `document`/`<unit>`/`template` entities plus `add*To<Unit>` verbs. If you are
building an iWork-class app, adopt all three in parallel; the shapes rhyme.

### 3.5 Counting the surface

| Domain | Intents | Entities | Enums |
|---|---:|---:|---:|
| audio | 7 | 18 | 6 |
| calendar | 3 | 3 | 4 |
| camera | 5 | 0 | 3 |
| clock | 10 | 2 | 2 |
| files | 5 | 1 | 0 |
| mail | 12 | 5 | 0 |
| maps | 6 | 6 | 7 |
| messages | 5 | 4 | 5 |
| notes | 2 | 3 | 0 |
| phone | 1 | 1 | 1 |
| photos | 28 | 3 | 4 |
| reminders | 8 | 5 | 2 |
| system | 2 | 0 | 0 |
| assistant | 1 | 0 | 0 |
| visualIntelligence | 1 | 0 | 0 |
| books | 9 | 3 | 12 |
| browser | 13 | 5 | 1 |
| journal | 5 | 1 | 0 |
| presentation | 14 | 3 | 0 |
| reader | 9 | 2 | 1 |
| spreadsheet | 14 | 3 | 0 |
| whiteboard | 7 | 2 | 2 |
| wordProcessor | 9 | 3 | 0 |
| **Total** | **~177** | **~73** | **~50** |

Totals are approximate: they count documented leaf schemas and exclude container/protocol
symbols (`AppSchema.MailIntent` etc.). Deprecated schemas are included in the counts.

**What is conspicuously absent:** fitness/workout, health, finance/banking, shopping/commerce,
travel/booking, food ordering, ride-hailing, social feeds, developer tools, education/learning,
smart-home (that lives in HomeKit), games. An app in any of those categories has **no primary
schema domain to adopt**, and therefore no route to un-app-qualified Siri actionability. This is
the direct structural cause of forum thread 837249 (hiking/cycling app).

---

## 4. The schema macro system

Source: `https://sosumi.ai/documentation/appintents/making-actions-and-content-discoverable-by-apple-intelligence`
and `.../app-schema-domains`.

Three macros, one per kind:

```swift
@AppEntity(schema: .photos.asset)     // content
@AppIntent(schema: .photos.openAsset) // actions
@AppEnum(schema: .photos.assetType)   // property value sets
```

### 4.1 Discovery vs. action — Apple's own framing

This is the cleanest statement of the distinction in the whole doc set, and it maps exactly
onto the forum pain. From "Making actions and content discoverable by Apple Intelligence":

- **Discovery is a runtime concern, satisfied by indexing.** *"Submit your entities to the
  Spotlight semantic index so the system indexes your app's content and matches it to
  requests."*
- **Action is a build-time concern, satisfied by schemas.** Schema macros plus the required
  properties are what let Apple Intelligence interpret a request and invoke your intent.

> *"Without both layers, Apple Intelligence cannot act on user requests involving your
> entities."*

So the forum observation — "Siri can find my entity but can't do anything with it" — is not a
bug. It is the documented architecture. Indexing buys discovery; only a schema buys action.

### 4.2 Schemas are enforced at build time with Fix-Its

Each schema defines mandatory properties. Per the same page: *"If your type is missing a
required property, Xcode generates an error at build time with a Fix-It that adds it for you."*

Example — `.photos.asset` requires:

```swift
var displayRepresentation: DisplayRepresentation
var id: Int
var creationDate: Date?
var assetType: PhotoAssetType?
var isFavorite: Bool
var isHidden: Bool
```

Example — `.photos.openAsset` requires:

```swift
var target: <EntityType>
func perform() async throws -> some IntentResult
```

Note `id: Int` on `.photos.asset` — schemas can dictate your **identifier type**, not just
property presence. That is a real modelling constraint, not a formality.

### 4.3 Xcode tooling around schemas (WWDC26 session 240, ch. 21:09)

- **Schema completion** — autocomplete of available schemas grouped by domain. Typing the
  domain prefix plus underscore (`system_`, `mail_`, ...) surfaces the template list.
- **Missing schema detection** — build-time errors for incomplete schema adoptions.
- **Fix-Its that generate related schemas.** The session's example: adopting `sendMessage`
  without `draftMessage` is flagged, because Siri needs both to complete a conversation flow.

That last point is a genuinely non-obvious requirement: **schemas come in conversational sets.**
Adopting one verb of a flow and not its siblings produces a build error, not a silent partial
experience.

---

## 5. On-screen awareness — the actual recipe

This is the highest-value section. Sources: WWDC26 session 343 (ch. 16:22 "Onscreen
awareness"), session 240 (ch. 16:00 "Working across apps: onscreen awareness"),
`https://sosumi.ai/documentation/appintents/providing-contextual-cues-to-apple-intelligence-and-siri`,
and Apple Developer Forums thread 838329.

### 5.1 The core type

Everything routes through one type:

```swift
EntityIdentifier(for: SongEntity.self, identifier: track.id)
```

`EntityIdentifier` is a persistent reference binding a piece of UI to a specific `AppEntity`
instance. You attach it to UI in one of several ways depending on the shape of your screen.

### 5.2 The four annotation shapes

**(a) One primary entity fills the screen — `NSUserActivity`.**

```swift
struct NowPlayingView: View {
    @Environment(PlaybackController.self) private var playback

    var body: some View {
        VStack { /* player UI */ }
        .userActivity("cosmotunes.nowPlaying", isActive: playback.currentTrack) { activity in
            activity.title = playback.currentTrack?.title
            activity.appEntityIdentifier = EntityIdentifier(
                for: SongEntity.self,
                identifier: playback.currentTrack.id
            )
        }
    }
}
```

Session 240 gives the selection rule: use `NSUserActivity` when there is a *single primary
item* on screen (a document, a message composition); use view annotations when *multiple
meaningful items* are visible.

**(b) One entity among many — `.appEntityIdentifier(_:)`.**

```swift
List {
    ForEach(messages) { message in
        MessageRow(message: message)
            .appEntityIdentifier(
                EntityIdentifier(for: MessageEntity.self, identifier: message.id)
            )
    }
}
```

**(c) Lists and collections — `.appEntityIdentifier(forSelectionType:_:)`.**

```swift
List {
    ForEach(playlist.tracks) { track in
        PlaylistTrackRow(track: track)
    }
}
.appEntityIdentifier(forSelectionType: GeneratedTrack.ID.self) { trackID in
    EntityIdentifier(for: SongEntity.self, identifier: trackID)
}
```

Session 343's stated benefit: **lazy fetching**, and it *"discovers selected/scrolled-off
entities"* — i.e. this variant covers entities not currently rendered, which the per-row
modifier cannot. This is what makes "play the third one" work on a long list.

**(d) Custom canvases and non-standard views — `appEntityUIElements(_:)` / `AppEntityUIElement`.**

```swift
AppEntityUIElement(
    identifier: EntityIdentifier(for: StickyNote.self, identifier: note.id),
    bounds: note.frame,
    state: State(isSelected: note.isSelected)
)
```

`AppEntityUIElement` bundles identifier **+ bounds + selection state**, which is what lets the
system reason spatially about a freeform canvas. Session 343 points at `PianoRollView` in the
CosmoTunes sample as the worked example.

UIKit/AppKit equivalents:
- `appEntityIdentifier` property on responder objects
- `appEntityUIElementProvider` closure property on views
- `AppEntityAnnotatable` protocol
- Data sources: `UITableViewAppIntentsDataSource`, `NSTableViewAppIntentsDataSource`,
  `UICollectionViewAppIntentsDataSource`, `NSCollectionViewAppIntentsDataSource`

### 5.3 Fast resolution — `displayRepresentations(for:requestedComponents:)`

Implement this on your `EntityQuery` so the system can resolve on-screen entities without
materializing full entities:

```swift
extension PlaylistQuery {
    func displayRepresentations(
        for identifiers: [PlaylistEntity.ID],
        requestedComponents: DisplayRepresentation.Components = .text
    ) async throws -> [PlaylistEntity.ID: DisplayRepresentation] {
        let entities = try await model.playlistEntities(for: identifiers)
        var result: [PlaylistEntity.ID: DisplayRepresentation] = [:]
        for entity in entities {
            result[entity.id] = await entity.displayRepresentation(with: requestedComponents)
        }
        return result
    }
}
```

`DisplayRepresentation.Components` lets the system ask for text only vs. text+image, so it can
avoid image work when it only needs to match a name.

### 5.4 Handing content to ANOTHER app — where it gets hard

Annotation makes an entity *referenceable* ("this", "that one"). Moving its **payload** across
an app boundary is a separate mechanism, and it is where the forum evidence diverges sharply
from the documentation's optimism.

**The documented route — `Transferable` + `IntentValueRepresentation`** (session 240, ch. 15:39):

```swift
extension ContactEntity: Transferable {
    static var transferRepresentation: some TransferRepresentation {
        IntentValueRepresentation(
            exporting: \.person,
            importing: { intentPerson in
                let contact = Contact(importing: intentPerson)
                ContactManager.shared.contacts.append(contact)
                return contact.entity
            }
        )
    }
}
```

`IntentValueRepresentation` bridges your entity to **system intent value types** —
`IntentPerson`, `PlaceDescriptor`, `PersonNameComponents` are the ones named in the contextual
cues doc. Pair it with `IntentValueQuery` to resolve an incoming system value onto an entity
you already have:

```swift
struct ContactEntityQuery: IntentValueQuery {
    func values(for input: [IntentPerson]) async throws -> [ContactEntity] {
        let names = input.map(\.displayName)
        let contacts = try model.mainContext.fetch(FetchDescriptor<Contact>())
        return contacts.filter { c in
            names.contains { c.name.localizedStandardContains($0) }
        }.map(\.entity)
    }
}
```

`exporting:` alone = resolve-or-nothing. Adding `importing:` = the receiving app **creates**
something new from the incoming value.

**Note the shape of the bridge.** `IntentValueRepresentation` maps onto a *system* value type.
There is a system type for a person. There is one for a place. As far as I could determine
there is **no general system value type for "an arbitrary image my app rendered"** — which is
exactly the hole thread 838329 fell into.

### 5.5 The verified working recipe for an on-screen image (forum thread 838329)

This is the single most actionable artifact in this pass. It is a **community** solution
(poster `J0hn`, marked as the recommended answer), **confirmed working on device on iOS 27**,
and it is *not* what the documentation leads you to.

**What did NOT work** — plain custom `AppEntity` + `Transferable` + `.appEntityIdentifier`:

```swift
struct OnScreenImageEntity: AppEntity, Transferable {
    static let typeDisplayRepresentation = TypeDisplayRepresentation(name: "On-Screen Image")
    static let defaultQuery = Query()
    let id: String

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(exportedContentType: .plainText) { … }
        DataRepresentation(exportedContentType: .png)       { … }
    }

    struct Query: EntityQuery {
        func entities(for ids: [String]) async throws -> [OnScreenImageEntity] {
            logger.notice("entities(for:) CALLED \(ids)")   // <- NEVER FIRES
            return ids.filter { store.isCurrent($0) }.map(OnScreenImageEntity.init)
        }
    }
}

Image(uiImage: image)
    .appEntityIdentifier(EntityIdentifier(for: OnScreenImageEntity.self, identifier: id))
```

**What DOES work** — adopt `.files.file`, use `FileEntityIdentifier`, export via
`FileRepresentation`:

```swift
@AppEntity(schema: .files.file)
struct MyFileEntity { /* schema-required properties */ }
```

UIKit hook (note the delegate method name — this is the collection-view entry point):

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

Transfer representation — **`FileRepresentation`, not `DataRepresentation`**:

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
            let attributes = try? FileManager.default
                .attributesOfItem(atPath: received.file.path())
            return <ENTITY>(
                id: try FileEntityIdentifier.file(url: received.file),
                creationDate: attributes?[.creationDate] as? Date,
                fileModificationDate: attributes?[.modificationDate] as? Date,
                name: received.file.lastPathComponent
            )
        })
}
```

**Result:** *"Send this to <contact>" now works and Siri lifts the on-screen image to another
app (confirmed on device iOS 27).*

**The catch, raised by the original poster and unrefuted:** `.files.file` requires **a real
file on disk at resolution time**. `FileEntityIdentifier.file(url:)` needs a URL, and
`entity.id.fileURL` must resolve. Transient in-memory renders — the exact case the poster
started with — have no supported path. If your app generates an image on the fly, you must
write it to disk to hand it off.

### 5.6 The contradiction worth flagging

The contextual cues documentation says, of schema adoption for on-screen annotation:

> *"Schema application is optional but recommended for consistency."*

The observed behaviour in thread 838329 is that on iOS 27 beta 3, a non-schema entity was
**never resolved** for hand-off — `entities(for:)` never fired for the Siri paths — while the
schema-typed `.files.file` entity resolved and transferred correctly.

Both statements can be true if "optional" governs *annotation/reference* ("this") while
schemas govern *transfer*. That is my reading, and it is consistent with the discovery-vs-action
split in Section 4.1. But **the docs do not say this anywhere I found**, and a developer
reading "optional but recommended" will reasonably conclude the custom-entity route is
supported and then lose days. Flagging as **UNVERIFIED interpretation** of a real documentation
gap.

### 5.7 Two paths, not one — screenshot vs. entity resolution

Thread 838329's instrumentation is the best available evidence on how the system actually
routes on-screen requests on iOS 27 beta 3:

| Request | Path taken | Evidence |
|---|---|---|
| "Describe this image" | **Screenshot / OCR** | Responses referenced app UI chrome; `entities(for:)` never called |
| "Create a note for this" | **Screenshot / OCR** | same |
| "Send this to <contact>" | Entity resolution — **failed** for custom entity | Siri: *"I can't attach the image directly from your screen"* |
| ChatGPT hand-off | Entity resolution — **fired**, then stalled | `entities(for:)` called; Siri then said *"could not clarify what you mean"* |
| Old `NSUserActivity.appEntityIdentifier` route | **Never consumed at all** | no callbacks |

Two operational takeaways: descriptive on-screen questions do **not** consult your entities at
all (they screenshot), and only hand-off style requests enter entity resolution. This directly
explains thread 837249's observation (Section 11) that Siri read visible text off the current
tab and could not see data on other tabs — that developer was on the **screenshot path the
whole time**, which is why their `EntityQuery` fired but returned nothing useful.

---

## 6. Query protocols — which one, when

Consolidated from sessions 240 and 343 and the framework docs. Picking the wrong query
protocol is a common cause of "Siri can't find my stuff".

| Protocol | Input | Use when |
|---|---|---|
| `EntityQuery` | `[ID]` via `entities(for:)` | Baseline. Resolve identifiers back to entities. |
| `EntityStringQuery` | `String` via `entities(matching:)` | You **cannot index ahead of time**. You own the search logic. |
| `IndexedEntityQuery` | Spotlight reindex requests | You use `IndexedEntity` and need to service reindex callbacks. |
| `IntentValueQuery` | **Structured system types** via `values(for:)` | Large/server-side/fast-changing data; Visual Intelligence input; resolving `IntentPerson`/`AudioSearch`. |
| `UniqueAppEntityQuery` | — | Singleton entities (2024 addition). |

`EntityStringQuery` (session 240):

```swift
struct ContactQuery: EntityStringQuery {
    func entities(matching string: String) async throws -> [ContactEntity] {
        let predicate = #Predicate<Person> { $0.name.localizedStandardContains(string) }
        let matches = try modelContext.fetch(FetchDescriptor<Person>(predicate: predicate))
        return matches.map(\.entity)
    }
}
```

`IntentValueQuery` with structured criteria (session 343). Note it can return **multiple entity
types**, unlike `EntityQuery`:

```swift
struct AudioIntentValueQuery: IntentValueQuery {
    func values(for input: AudioSearch) async throws -> [AudioEntity] {
        switch input.criteria {
        case .searchQuery(let query): return try await searchResults(for: query)
        case .unspecified:            return try await likedSongResults()   // "Play CosmoTunes"
        // also a .url case — "play that playlist Glow sent me"
        }
    }
}
```

### 6.1 `.system.searchInApp` — the escape hatch, and the answer to the deprecations

Session 343 ch. 15:27 names the replacement for the deprecated `.system.search`:

```swift
@AppIntent(schema: .system.searchInApp)
struct SearchAudioLibraryIntent {
    var criteria: StringSearchCriteria

    func perform() async throws -> some IntentResult {
        navigation.searchText = criteria.term
        navigation.selectedTab = .library
        return .result()
    }
}
```

The stated benefit is the important part: it *"runs Siri's search string through your custom
search UI, **regardless of domain adoption or entity indexing**."*

**This is the single most useful fact for a developer with no applicable schema domain.**
`.system.searchInApp` lives in a **primary** domain, takes an unstructured string, and imposes
no requirement that you adopt a content domain or index anything. For the hiking app in thread
837249, or any app in a category Apple has not modelled, this is the one schema-tier hook that
is actually reachable. It cannot answer a question in Siri's own voice — it navigates the user
into your app's search UI — but it is a supported, un-app-qualified Siri entry point.

> **UNVERIFIED naming detail.** `.system.searchInApp` comes from session 343's transcript
> content. The domain page I fetched (`app-schema-domain-system-and-in-app-search`) listed only
> `open` and `search` (deprecated) as leaf symbols and did not list `searchInApp`. The page
> *title* — "System and in-app search" — corroborates that in-app search belongs there. Likely
> a doc-page lag; verify against the current header before relying on the exact spelling.

---

## 7. Spotlight, `IndexedEntity`, and the semantic index

Source: `https://sosumi.ai/documentation/appintents/making-app-entities-available-in-spotlight`,
session 343 ch. 11:59.

### 7.1 Minimal adoption

> *"Adding this protocol to your entity's declaration is the only requirement for support."*

`IndexedEntity` supplies default implementations for all defined properties; you override
selectively.

```swift
@AppEntity(schema: .messages.message)
struct MessageEntity: IndexedEntity {
    @Property(indexingKey: \.textContent)
    var body: AttributedString?
}
```

### 7.2 Indexing

```swift
try await CSSearchableIndex(name: "AppIntentsTravelTracking_Landmarks")
    .indexAppEntities(landmarkEntities)
```

API: `CSSearchableIndex.indexAppEntities(_:priority:)`. Docs direct you to use a **named**
index rather than the default one in production.

Maintenance duties (session 343): add on create, update when key properties change, delete on
removal.

### 7.3 Property wrappers and indexing keys

`@Property`, `@ComputedProperty`, `@DeferredProperty` all accept:
- `indexingKey:` — bind to an **existing Spotlight key** via key path (e.g. `\.contentDescription`, `\.textContent`)
- `customIndexingKey:` — bind to an app-defined key via `CSCustomAttributeKey`

### 7.4 Servicing reindex requests — `IndexedEntityQuery`

```swift
func reindexEntities(
    for identifiers: [PhotoEntity.ID],
    indexDescription: CSSearchableIndexDescription
) async throws

func reindexAllEntities(
    indexDescription: CSSearchableIndexDescription
) async throws
```

Session 343 notes you need not implement this if you already use Core Spotlight APIs directly.

### 7.5 Lexical AND semantic

The docs state Spotlight enables *"fast lexical and semantic searches"* — word-matching and
meaning-based retrieval over the same index. This dual nature is the hinge for Section 12.

---

## 8. Snippets

Source: `https://sosumi.ai/documentation/appintents/snippetintent`.

```swift
protocol SnippetIntent : AppIntent where Self.PerformResult : ShowsSnippetView
```

**Availability: iOS 26.0+ / macOS 26.0+ / watchOS 26.0+ / visionOS 26.0+ / tvOS 26.0+.**
So `SnippetIntent` is a **2025 (OS 26) feature, not new in 2026** — the updates page lists it
under June 2025. It is prior art that the 2026 Siri work builds on, not part of this release.

Purpose: display *"custom SwiftUI views to show people the result of their action, confirm a
selection, and more."* Snippets support **interactive** elements — buttons and toggles that
trigger further app intents.

Two behaviours that bite:

1. **The system can call a `SnippetIntent` multiple times.** Your `perform()` must re-fetch
   current state each call so the view reflects user interaction. Do not cache.
2. **Snippet-only intents are non-discoverable by default.** Set `isDiscoverable = true`
   to surface them in Shortcuts or Spotlight.

Related: `ShowsSnippetView` (the result conformance), `EmptySnippetIntent` (default empty
implementation).

Session 343 shows the non-`SnippetIntent` route — returning a snippet view straight from a
schema intent:

```swift
@AppIntent(schema: .audio.addToPlaylist)
struct AddToPlaylistIntent {
    func perform() async throws -> some IntentResult & ProvidesDialog & ShowsSnippetView {
        let view = PlaylistSnippetView(playlist: updatedEntity, tracks: updated.tracks)
        return .result(dialog: dialog, view: view)
    }
}
```

---

## 9. What changed in the 2026 release

Source: `https://sosumi.ai/documentation/updates/appintents` plus WWDC26 sessions 240/343/345.

> **Date-label caveat.** The updates page section I read was labelled in a way that mixed
> "June 2026" with an OS number that did not match, and session 345's framing referred to
> "the 2027 releases". I could not reconcile these from the pages themselves. The **API names
> below are solid**; treat the exact release-year labelling as **UNVERIFIED**, and note that
> session 345's contents may target a later release than sessions 240/343.

### 9.1 New for Apple Intelligence / Siri

| API | What it does |
|---|---|
| `SyncableEntity` | Declare entity IDs stable across devices, for multi-device Siri conversations |
| `SyncableEntityIdentifier<Local, Stable>` | Pair a local ID with a stable one when your IDs are device-local |
| `OwnershipProvidingEntity` | Declare entity as private/shared/public so Siri knows when to confirm |
| `EntityOwnership` | `.unknown` (private, default), `.shared`, `.public` |
| `RelevantEntities` | Push entities to the system tagged with the context they're relevant in |
| `IntentValueRepresentation` | Bridge an app entity to a system intent value type |

`RelevantEntities` usage (session 345):

```swift
let workoutContext = AppEntityContext.audio(.workout(activityType: .running))
try await RelevantEntities.shared.updateEntities([dailyRun, runningMix], for: workoutContext)
try await RelevantEntities.shared.removeAllEntities(for: workoutContext)
```

`OwnershipProvidingEntity` (session 343) — this is what drives Siri's "are you sure?" prompts:

```swift
@AppEntity(schema: .calendar.event)
struct EventEntity: OwnershipProvidingEntity {
    var ownership: EntityOwnership { attendees.isEmpty ? .unknown : .shared }
}
```

### 9.2 New intent execution model

| API | What it does |
|---|---|
| `LongRunningIntent` | Break the ~30-second execution ceiling |
| `performBackgroundTask(options:operation:)` | The wrapper that does it |
| `LongRunningTaskOptions` | Config for extended tasks |
| `CancellableIntent` | `onCancel(reason:)` cleanup hook |
| `IntentCancellationReason` | user-cancel / system timeout / resource reclamation |
| `UndoableIntent` | Reverse an intent's effects |
| `IntentModes` | Control foreground vs. background execution |
| `IntentSystemContext.currentMode` | Inspect the mode at runtime |
| `IntentExecutionTargets` / `allowedExecutionTargets` | Pin execution to `.main`, `.appIntentsExtension`, `.widgetKitExtension`, or a set |
| `RunSystemShortcutIntent` | Run App Shortcuts / system actions / open another app **from interactive widgets** |

```swift
struct UploadPhotoIntent: LongRunningIntent, CancellableIntent {
    @Parameter var photo: IntentFile

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let result = try await performBackgroundTask {
            progress.totalUnitCount = Int64(chunks)
            for chunk in 1...chunks {
                try Task.checkCancellation()
                try await uploadChunk(chunk)
                progress.completedUnitCount = Int64(chunk)
            }
            return "Upload complete!"
        } onCancel: { reason in cleanup(for: reason) }
        return .result(dialog: "\(result)")
    }
}
```

`LongRunningIntent` requires progress reporting (builds on `ProgressReportingIntent`), surfaces
progress as a **Live Activity**, and supports background GPU access on capable devices.

### 9.3 New entity/parameter capabilities

| API | What it does |
|---|---|
| `EntityCollection<T>` | Carry identifiers only; resolve entities on demand |
| `AppUnionValue` / `@UnionValue` / `AppUnionValueCasesProviding` | One parameter, several entity types |
| `IndexedEntityQuery` | Service Spotlight reindex requests |
| `ValueRepresentation` | Share structured system types (e.g. `PlaceDescriptor`) across apps |
| Extended native types | `Duration`, `PersonNameComponents` get native pickers + Siri understanding |

`EntityCollection` — session 345 claims tagging 1000 photos went from slow to *"nearly
instant"*, because the system skips full entity resolution when the intent only needs IDs:

```swift
@Parameter var photos: EntityCollection<PhotoEntity>   // was: [PhotoEntity]
// then: modelData.tagPhotos(ids: photos.identifiers, tag: tag)
```

`@UnionValue`:

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

`ValueRepresentation` (session 345) vs. `IntentValueRepresentation` (session 240) — **two
similarly-named types appear across the sessions**, both concerned with exporting an entity as
a system value type. I could not determine from the fetched pages whether one supersedes the
other or they coexist at different layers. **UNVERIFIED — flagged as a naming hazard.**

### 9.4 Errors

- `AppIntentError.init(description:)` — construct with a localized description
- `CustomLocalizedStringResourceConvertible` — error wrapping
- `CustomAppIntentErrorConvertible` — listed under the framework's Errors topic

These matter for Section 13: they are the sanctioned way to stop internal errors leaking to
users.

### 9.5 Testing — `AppIntentsTesting`

New framework (`https://developer.apple.com/documentation/AppIntentsTesting`). Session 240
ch. 24:18 gives a four-stage ladder, which is a genuinely good adoption process:

1. **`AppIntentsTesting`** — invoke intents with test parameters, assert results like unit
   tests. No Siri needed. Validates business logic.
2. **Shortcuts app** — validates intent *shape* and configuration.
3. **Spotlight** — validates indexing and discoverability.
4. **Siri** — end-to-end natural language, entity resolution, cross-app workflow.

Debug at the lowest stage that reproduces the failure. Most "Siri doesn't work" reports are
stage-2 or stage-3 problems misdiagnosed as stage-4.

---

## 10. WWDC26 sessions

All four session pages fetched successfully from `developer.apple.com/videos/play/wwdc2026/<n>/`.
The pages carry **full chapter lists, resource links, and substantial code**; direct MP4
download URLs are also exposed. **None of these are in our transcript corpus** — this was the
gap that motivated this pass, and it is real.

### Session 240 — "Build intelligent Siri experiences with App Schemas"
Presenter: Dan Niemeyer, Swift Intelligence Frameworks. Sample app: **UnicornChat** (messaging).

| Time | Chapter |
|---|---|
| 0:00 | Introduction |
| 1:06 | What's new in Siri — three capabilities: access app entities, take actions, understand onscreen context |
| 4:06 | Contributing content with App Entities |
| 6:21 | Entity resolution and `IndexedEntity` |
| 9:49 | Making actions available |
| 12:03 | Adopting a schema domain in UnicornChat (Messages domain, end-to-end) |
| 15:39 | Moving content across apps |
| 16:00 | Working across apps: onscreen awareness |
| 21:09 | Best practices |
| 24:18 | Testing your integration |
| 26:21 | Next steps |

This is **the** foundational session for this topic. Ch. 1:06's three-capability framing —
access entities / take actions / understand onscreen context — is Apple's own decomposition and
maps onto Sections 4, 3 and 5 here respectively.

### Session 343 — "Explore advanced App Intents features for Siri and Apple Intelligence"
Presenter: Antonio Cancio, App Intents team. Samples: **CosmoTunes**, **UnicornChat**,
**CometCal**. Prerequisite: basic App Intents + App Schemas.

| Time | Chapter |
|---|---|
| 0:00 | Introduction |
| 1:59 | Customize how Siri responds |
| 4:20 | Visual responses |
| 6:22 | Interaction donations |
| 9:46 | Confirmations and entity ownership |
| 11:59 | Semantic index with `IndexedEntity` |
| 13:32 | Structured search with `IntentValueQuery` |
| 15:27 | In-app search |
| 16:22 | **Onscreen awareness** |
| 20:51 | Leverage existing integrations |
| 23:30 | Next steps |

**Ch. 16:22 is the richest single source on on-screen awareness in existence** and supplied
most of Section 5. Ch. 20:51 supplied the system-integration annotations in 10.1 below.

### Session 344 — "Code-along: Make your app available to Siri"
Presenter: Justin Kang, Swift Intelligence Frameworks. Sample: **CometCal** (SwiftUI calendar).
End-to-end adoption of the `.calendar` domain, including `TransientAppEntity`,
`EnumerableEntityQuery`, snippet views, and `IntentParameter.valueState`.

| Time | Chapter |
|---|---|
| 0:00 | Introduction | 1:43 | App Schemas and the plan |
| 3:44 | Build the `CalendarEntity` | 8:00 | Build the `AttendeeEntity` |
| 10:30 | Build the `EventEntity` | 14:34 | Open events with `OpenIntent` |
| 15:30 | Onscreen awareness | 17:18 | Create events with Siri |
| 19:24 | Update events | 21:30 | Custom snippet views |
| 22:30 | Delete events | 23:35 | Next steps |

Two details worth extracting from 344 that appear nowhere else I read:

**`IntentParameter.valueState` — three-state optionals.** This solves the "did the user say to
clear this, or not mention it?" problem:

```swift
switch $recurrence.valueState {
case .set(let value):  // .set with a value = change it; .set with nil = explicitly clear it
case .unset:           // not part of the request — leave alone
}
```

**`TransientAppEntity`** for sub-objects with no independent identity — no query, no index,
reachable only through their parent:

```swift
@AppEntity
struct AttendeeEntity: TransientAppEntity {
    var person: IntentPerson
    var status: AttendeeStatus
    var type: AttendeeType
    var isOptional: Bool
}
```

Also note `LocationUnion` / `AlarmUnion` in `EventEntity` — union-typed properties are how the
`.calendar` schema models "a location is either a `PlaceDescriptor` or a `String`."

> **Discrepancy to verify.** Session 344's on-screen awareness snippet as rendered showed
> `.appEntityIdentifier(event.id.uuidString)` (a bare String) and
> `.userActivity("event", value: event.id.uuidString)`. Session 343 and the contextual-cues doc
> both show the modifier taking an `EntityIdentifier(for:identifier:)`. **Trust the 343 form.**
> The 344 rendering is probably summarization loss. **UNVERIFIED.**

### Session 345 — "Discover new capabilities in the App Intents framework"
Sample: **Landmarks Travel Tracking**. Covers `ValueRepresentation`, `RelevantEntities`,
`EntityCollection`, `SyncableEntity`, richer parameter types, `@UnionValue`,
`LongRunningIntent`, `ExecutionTargets`.

| Time | Chapter |
|---|---|
| 0:00 | Introduction | 2:40 | Share entities across apps with `ValueRepresentation` |
| 3:45 | Register relevant entities with `RelevantEntities` | 7:05 | Handle entities efficiently with `EntityCollection` |
| 8:55 | Use entities across devices with `SyncableEntity` | 11:01 | Richer parameter types |
| 12:38 | Union value parameters | 13:26 | Extend execution with `LongRunningIntent` |
| 15:27 | Target the right process with `ExecutionTargets` | 17:14 | Next steps |

Session 345 explicitly does **not** cover `UndoableIntent`, `IntentModes`, or `SnippetIntent`,
despite the first two appearing on the updates page — so those have no session coverage I found.

### 10.1 System-integration entity annotations (session 343, ch. 20:51)

Beyond the screen, `EntityIdentifier` can be attached to three other system surfaces. This is
a genuinely under-known capability:

| Surface | Property | Type | Enables |
|---|---|---|---|
| `UNMutableNotificationContent` | `appEntityIdentifiers` | `[EntityIdentifier]` | Reply to an announced notification on AirPods |
| `MusicContent` (via `MediaSessionRepresentable`) | `appEntityIdentifiers` | `[EntityIdentifier]` | "Play the live version" while something is playing |
| `AlarmKit` `AlarmConfiguration` | `appEntityIdentifier` | `EntityIdentifier` | "Snooze it" |

```swift
content.appEntityIdentifiers = [
    EntityIdentifier(for: MessageEntity.self, identifier: message.id)
]
```

For Now Playing, order the array **most specific to least specific** — song, then artist, then
playlist:

```swift
content.appEntityIdentifiers = [
    EntityIdentifier(for: SongEntity.self,     identifier: track.id),
    EntityIdentifier(for: ArtistEntity.self,   identifier: track.session.artistName),
    EntityIdentifier(for: PlaylistEntity.self, identifier: currentPlaylist.id),
]
```

The contextual-cues doc gives the Media Player key as
`MPNowPlayingInfoPropertyAppEntityIdentifiers`.

**Constraint:** persistent entities only. `TransientAppEntity` is **not supported** on these
surfaces.

### 10.2 Interaction donations (session 343, ch. 6:22)

Siri learns from Siri interactions automatically. It does **not** learn from your UI. Donate
those explicitly:

```swift
let intent = SendMessageIntent()
intent.destination = .recipients(conversation.recipients.map(\.entity))
try await IntentDonationManager.shared.donate(intent: intent, result: .result(value: result))
```

Rules given: donate **only** UI interactions (never Siri-originated ones — double-counting),
donate accurately, and note that **excessive donations are ignored**. Good fits: ongoing
activities like Maps navigation or Clock stopwatches.

---

## 11. Developer forum evidence

### 11.1 Thread 838329 — the on-screen image hand-off (4 replies, 246 views)
`https://developer.apple.com/forums/thread/838329` — FrankSchlegel, 17 Jul 2026.
Feedback filed: **FB23813341**.

Full technical content in Section 5.5 and 5.7. The structure of this thread is the story of the
whole area in miniature:

1. Developer follows the documentation exactly ("Making onscreen content available to Siri and
   Apple Intelligence" + the WWDC sessions).
2. It does not work. Instrumented logging proves the callbacks never fire.
3. **Apple's DTS engineer does not answer the technical question.** The reply, quoted:

   > *"There is so much you have provided including issues making onscreen content available to
   > Siri and Apple Intelligence and providing contextual cues to Apple Intelligence and Siri...
   > Because you submitted a focused sample and the same explanation on a good written bug,
   > I'll let the team take over all the issues."*

   The developer is routed to Feedback Assistant. No API guidance is given.
4. **Another developer supplies the working answer.** `J0hn`'s `.files.file` +
   `FileEntityIdentifier` + `FileRepresentation` recipe is marked as the recommended answer and
   confirmed on device.
5. The original poster accepts it but restates the unanswered architectural question:

   > *"I wonder if this more generic approach shouldn't also work... Is on-screen consumption
   > intended to be limited to the predefined assistant schemas, or should a custom `AppEntity`
   > + `Transferable` also be a supported way to expose arbitrary on-screen content?"*

   **This question is still open.** Nobody from Apple answered it.

### 11.2 Thread 837249 — on-screen awareness without a schema (0 replies, 205 views)
`https://developer.apple.com/forums/thread/837249` — haozes, 8 Jul 2026.

A hiking/cycling app wants Siri to answer, mid-activity: *"How much farther to the
destination?"*, *"How far have I already gone?"*, *"How much elevation gain is left?"*

Observed behaviour:
- Siri **executed** the custom `EntityQuery` (`ToobooWorkoutSessionQuery`) but did not use the
  `AppEntity` data.
- It read **visible on-screen text** — *"Distance: 0.21 mi"*, *"Remaining Distance: 0.14 mi"* —
  from the current tab only.
- It could not reach data on **other tabs** (heart rate, average speed).
- Conclusion drawn by the developer: Siri is reading the screen, not querying the entity.

The developer's own diagnosis is almost certainly right, and Section 5.7 explains why: these
are *descriptive* on-screen questions, which take the **screenshot/OCR path** and never consult
app entities. The developer built the entity plumbing for a request class that does not use it.

Their fallback — multiple Intents plus App Shortcuts — works but forces the user to say the app
name, which they call unnatural for a hands-free cycling context.

**Zero replies. Apple never answered.** Two hundred views and no response is itself a finding:
this is not a niche question, and there is no first-party answer to point at.

Relevant structural fact from Section 3: **there is no fitness/workout schema domain.** `.maps`
covers starting and stopping navigation but has no schema for *querying progress*. This
developer had no schema to adopt even if they wanted to. The most promising available route is
`.system.searchInApp` (Section 6.1), which would at least give an un-app-qualified entry point
— though it navigates rather than answers.

### 11.3 Thread 775988 — `DynamicOptionsProvider` + search (Mar 2025)
`https://developer.apple.com/forums/thread/775988` — alexander216.
Wants sectioned **and** searchable `EntityPropertyQuery` options. `EntityStringQuery` gives
search; `DynamicOptionsProvider` gives sections; combining them loses search. Predates the 2026
work but shows the query-protocol composition problem is long-standing.

### 11.4 Threads 836760 and 835211 — Foundation Models coupled to Siri

**`https://developer.apple.com/forums/thread/836760`** (1 reply, 257 views) — "Foundation models
tied to Siri in Mac OS beta 2". Developer reports FM unavailable when Siri AI is off, and asks
what that means in Europe. **Apple Frameworks Engineer replied** — one of the few substantive
Apple answers in this whole cluster:

> *"The Foundation Models framework should be available in Europe even if Siri AI is not
> enabled. Please file a bug report via Feedback Assistant and be sure to include a sysdiagnose
> to help us investigate."*

So the coupling is **a bug, not the design**. Useful and quotable.

**`https://developer.apple.com/forums/thread/835211`** (0 replies, 249 views) — corroborating
report from iOS 27 Beta 1: `SystemLanguageModel.default.availability` returns
`.appleIntelligenceNotEnabled` unless the user has enabled "Siri"/"Hey Siri" or "Press Side
Button for Siri". The poster notes this is odd given the new "pull down for Siri" UX. Unanswered.

Two independent reports on two platforms, one Apple confirmation that it is unintended.

### 11.5 The pattern across the cluster

Of the App Intents / Siri / on-screen threads examined: **one substantive Apple answer**
(836760, and it was about FM availability, not App Intents), **one deflection to Feedback
Assistant** (838329), and **the rest unanswered**. The one genuinely useful technical answer in
the cluster came from another developer, not Apple.

This confirms the premise of this research pass. Forum captures alone would badly under-serve
this topic; the sessions and docs had to be fetched first-party.

---

## 12. Connection to Foundation Models

Cross-reference: `/Volumes/ExtStor/FM and MLX and CoreAI/notes/transcripts/fm-ecosystem.md`,
PART C (`:1342` onward), our existing deep notes on WWDC26-246 and `SpotlightSearchTool`.

### 12.1 There is no direct App Intents -> `LanguageModelSession` bridge

I looked for one and did not find it. There is no `AppIntentTool`, no
`Tool` conformance on `AppIntent`, and nothing in the App Intents framework docs that exposes
entities to a `LanguageModelSession` directly. WWDC26-345's `Tool`-adjacent APIs are about
system execution targets, not about Foundation Models.

A blog-level summary encountered during search stated flatly that *"Foundation Models has no
direct Siri integration."* Consistent with everything else I read, but it is a secondary source
— treating as corroboration, not proof. **UNVERIFIED as a negative claim**; absence of evidence.

### 12.2 The real connection is indirect and runs through the Spotlight semantic index

This is the important architectural insight, and it ties this pass to notes we already have:

```
    @AppEntity + IndexedEntity
              |
              |  CSSearchableIndex.indexAppEntities(_:)
              v
    Spotlight semantic index  (lexical + semantic)
         /                \
        /                  \
       v                    v
  Siri / Apple          SpotlightSearchTool
  Intelligence          (_CoreSpotlight_FoundationModels overlay)
  entity resolution              |
                                 v
                        LanguageModelSession
```

**Both consumers read the same index.** Indexing your entities once serves Siri's entity
resolution *and* makes that content reachable by your own on-device model through
`SpotlightSearchTool`.

Our existing corpus already captured the hint. `fm-ecosystem.md:1397-1398` quotes WWDC26-246:

> *"Once your app has donated searchable items to Core Spotlight, **or indexed entities for
> Apple Intelligence**, we're ready to begin."*

At `fm-ecosystem.md:1400-1401` we flagged that clause as *"an interesting second on-ramp — App
Intents entity indexing also feeds this. **UNVERIFIED** how that path differs."*

**This pass resolves that open question.** The "second on-ramp" is exactly `IndexedEntity` +
`CSSearchableIndex.indexAppEntities(_:)` as documented in "Making app entities available in
Spotlight" (Section 7). It is not a different index — it is the *same* Core Spotlight index,
populated through the App Intents entity API instead of raw `CSSearchableItem`s. Search
corroboration: *"Entity schemas contribute your app's content to the Spotlight semantic index,
enabling personal context understanding with attribution back to your app."*

Practical consequence for anyone building both: **you do not need two indexing paths.** Adopt
`IndexedEntity`, index with `indexAppEntities`, and both Siri and `SpotlightSearchTool` see the
content. Choose the App Intents on-ramp when your content is already modelled as entities;
choose raw `CSSearchableItem` when it is not.

### 12.3 Where the two paths differ

| | App Intents on-ramp | Core Spotlight on-ramp |
|---|---|---|
| Unit | `AppEntity` conforming to `IndexedEntity` | `CSSearchableItem` |
| Index call | `CSSearchableIndex.indexAppEntities(_:priority:)` | `CSSearchableIndex.indexSearchableItems(_:)` |
| Attribute mapping | `@Property(indexingKey:)` / `customIndexingKey:` | `CSSearchableItemAttributeSet` directly |
| Reindex servicing | `IndexedEntityQuery` | `CSSearchableIndexDelegate` |
| Also gives you | Siri actionability (with a schema), on-screen annotation targets | nothing beyond search |
| `SpotlightSearchTool` full-item recovery | **UNVERIFIED** | `searchableItems(forIdentifiers:)` on the delegate (`fm-ecosystem.md:1541`) |

That last row is a **concrete open question**. Our notes at `fm-ecosystem.md:1524-1532` record
that `SpotlightSearchTool` relies on a `CSSearchableIndexDelegate` method to recover a full
`CSSearchableItem` by unique identifier, so the model can manage context efficiently:

```swift
extension MyIndexDelegate: CSSearchableIndexDelegate {
    func searchableItems(forIdentifiers identifiers: [String]) -> [CSSearchableItem] { … }
}
```

If you indexed via `indexAppEntities` rather than `indexSearchableItems`, **it is not documented
anywhere I found what identifiers arrive at that delegate, or whether the delegate is consulted
at all.** An app doing entity-based indexing and wanting rich `SpotlightSearchTool` results may
need to implement both. Worth an empirical test.

### 12.4 The availability coupling (Section 11.4)

Both frameworks sit behind Apple Intelligence enablement. Two beta reports had
`SystemLanguageModel.default.availability` returning `.appleIntelligenceNotEnabled` unless Siri
was switched on. Apple's Frameworks Engineer stated FM *"should be available in Europe even if
Siri AI is not enabled"* and asked for a bug report — so this is unintended. Anyone shipping an
FM feature should still handle `.appleIntelligenceNotEnabled` gracefully, because on current
betas it fires for reasons unrelated to the user's actual intent.

---

## 13. Known limitations and error behaviors

1. **The schema surface is closed and category-biased.** No fitness, health, finance, commerce,
   travel, food, transport, social, education, or gaming domain. Apps in those categories have
   no primary schema to adopt. (Section 3.5)

2. **Custom `AppEntity` = discoverable, not actionable.** Indexing buys discovery; only a schema
   buys action. Apple's own words: *"Without both layers, Apple Intelligence cannot act on user
   requests involving your entities."* (Section 4.1)

3. **Descriptive on-screen requests never consult your entities.** "Describe this",
   "create a note for this" take a screenshot/OCR path. `entities(for:)` is not called. Building
   entity plumbing for these requests is wasted work. (Section 5.7)

4. **On-screen hand-off of a non-file payload has no verified route.** `.files.file` +
   `FileEntityIdentifier` + `FileRepresentation` works; custom `AppEntity` + `Transferable` did
   not. And `.files.file` **requires a real file on disk at resolution time**, so transient
   in-memory renders must be written out first. (Section 5.5)

5. **Documentation contradiction.** "Schema application is optional but recommended for
   consistency" vs. observed non-resolution of non-schema entities. Unreconciled. (Section 5.6)

6. **Schemas dictate your data model.** `.photos.asset` requires `id: Int`. Required properties
   are build-time-enforced with Fix-Its. Schemas also come in **conversational sets** —
   `sendMessage` without `draftMessage` is a build error. (Section 4.2, 4.3)

7. **`TransientAppEntity` cannot be used** with notification / Now Playing / AlarmKit entity
   annotations. Persistent entities only. (Section 10.1)

8. **`SnippetIntent` may be invoked repeatedly.** `perform()` must re-fetch state; do not cache.
   Snippet-only intents are non-discoverable unless `isDiscoverable = true`. (Section 8)

9. **Excessive interaction donations are ignored.** Do not donate Siri-originated interactions.
   (Section 10.2)

10. **Deprecated generic search across four domains** — `.system.search`, `.browser.search`,
    `.books.search`, `.journal.search`, plus `.books.playAudiobook`. Generic search is migrating
    to Spotlight/`IndexedEntity` and to `.system.searchInApp`. (Sections 3.2, 6.1)

11. **Shortcuts-tier domains are not Siri-tier.** Eight of the 23 domains are grouped as
    Shortcuts-specific. (Section 3.1)

12. **`.assistant` is Japan-only** and is a side-button registration, not a general assistant
    hook. (Section 3.3)

13. **FM availability is coupled to Siri enablement on current betas.** Confirmed unintended by
    Apple. (Section 12.4)

### 13.1 On raw internal errors leaking to users

The premise for this pass noted developers seeing raw internal errors surface in Siri UI. **I
found no first-party documentation, session content, or Apple statement describing or
acknowledging that behaviour.** The forum threads I fetched (838329, 837249) report *unhelpful*
Siri responses — *"I can't attach the image directly from your screen"*, *"could not clarify
what you mean"* — but those are Siri's own phrasings, not leaked internals.

What the docs *do* provide is the machinery to prevent leakage:

- `AppIntentError` and its subtypes (`PermissionRequired`, `Unrecoverable`, `UserActionRequired`)
- `AppIntentError.init(description:)` — new, takes a localized description
- `CustomAppIntentErrorConvertible` and `CustomLocalizedStringResourceConvertible` — map your
  domain errors to something presentable

Guidance that follows: **never let a raw `Error` escape `perform()`.** Conform your error type
to `CustomAppIntentErrorConvertible` / `CustomLocalizedStringResourceConvertible` so whatever
Siri surfaces is a string you wrote.

**Marking the "raw internal errors" claim UNVERIFIED** pending a specific thread. If our corpus
has one, its thread ID should be added here and the full thread fetched.

---

## 14. Open questions / UNVERIFIED

1. **Is custom `AppEntity` + `Transferable` on-screen hand-off supposed to work?** The exact
   question FrankSchlegel asked and nobody answered. FB23813341 is the tracking radar.
2. **Exact tier semantics.** What capability does each of the three domain tiers actually
   confer? Inferred from grouping labels, never stated in prose.
3. **`.system.searchInApp` spelling and availability.** From session 343; the domain doc page
   still listed only `open` and `search` (deprecated).
4. **`ValueRepresentation` vs. `IntentValueRepresentation`.** Two similar names across sessions
   345 and 240. Relationship undetermined. Naming hazard.
5. **Release-year labelling.** Updates page mixed "June 2026" with a mismatched OS number;
   session 345 framed its content as "the 2027 releases". Unreconciled. API names are solid;
   which OS ships them is not.
6. **`SpotlightSearchTool` + `indexAppEntities` interop.** Does `CSSearchableIndexDelegate
   .searchableItems(forIdentifiers:)` get called for entity-indexed content? (Section 12.3)
7. **Session 344's `.appEntityIdentifier(String)` form.** Probably summarization loss; trust
   session 343's `EntityIdentifier(for:identifier:)`.
8. **The "raw internal errors" report.** No source located. (Section 13.1)
9. **Transient/in-memory content hand-off.** Is writing to disk genuinely the only route?
10. **`UndoableIntent` and `IntentModes`.** On the updates page, in no session I found. No
    usage examples located.
11. **Full session transcripts.** The session pages yield descriptions, chapters, resources and
    substantial code, but I did not confirm whether a complete verbatim transcript is
    retrievable. The MP4 URLs are exposed if transcription is ever wanted.

### 14.1 Sources that failed

| URL | Result |
|---|---|
| `https://sosumi.ai/documentation/appintents/making-onscreen-content-available-to-siri-and-apple-intelligence` | **HTTP 404.** The title is cited by name in forum thread 838329, so the article exists or existed. The live equivalent appears to be `providing-contextual-cues-to-apple-intelligence-and-siri`, which I fetched successfully. Possibly renamed. |
| `https://sosumi.ai/documentation/appintents/app-intent-domains` | Not the real path. Correct path is `app-schema-domains`. |

Everything else attempted returned usable content. **sosumi.ai is reliable for this material**
and should be the default route for Apple docs in future passes. Note that its summarizer will
refuse prompts phrased as "reproduce verbatim" on copyright grounds — phrase requests as
"extract the factual API reference data: symbol names and paths" and it complies fully.

---

## 15. Verdict

**Yes — there is enough verified material here to justify guides, and the gap is real.** The
WWDC26 sessions 240/343/344/345 are absent from our transcript corpus, and this is the topic
with the highest ratio of *documented API surface* to *corpus coverage* that I have seen.

Three guides. Not one — the audiences and the questions are genuinely different. Not more —
beyond three, the material starts repeating.

### Guide 1 — "App Schema Domains: the complete map of what Siri can do with your app"
*Reference. The artifact nobody else has.*

1. Why schemas exist: discovery vs. action, quoting Apple's own framing
2. The three macros and build-time enforcement (required properties, Fix-Its, conversational sets)
3. The three tiers and what each actually reaches
4. **Complete enumeration of all 23 domains** — every intent, entity and enum (Section 3)
5. Coverage analysis: which app categories have no domain, and what that means
6. Deprecations and the migration of generic search to Spotlight
7. Decision tree: pick your domain, or `.system.searchInApp`, or App Shortcuts

*This is the highest-value deliverable of the pass.* No equivalent enumeration exists in one
place, including in Apple's own docs, which spread it across 24 pages.

### Guide 2 — "On-screen awareness: making Siri understand 'this'"
*Recipe-driven. Where the pain is.*

1. The two paths — screenshot/OCR vs. entity resolution — and how to tell which you are on
2. `EntityIdentifier`, the one type everything routes through
3. The four annotation shapes: `NSUserActivity`, `.appEntityIdentifier`,
   `.appEntityIdentifier(forSelectionType:)`, `AppEntityUIElement` — with the selection rule
4. UIKit/AppKit: data sources, `AppEntityAnnotatable`, `appEntityUIElementProvider`
5. Fast resolution with `displayRepresentations(for:requestedComponents:)`
6. **The verified hand-off recipe** — `.files.file` + `FileEntityIdentifier` +
   `FileRepresentation`, complete and working, with the disk-file caveat stated up front
7. `Transferable` / `IntentValueRepresentation` / `IntentValueQuery` and their limits
8. Beyond the screen: notifications, Now Playing, AlarmKit
9. What does not work, and the open FB radar

*This directly answers both unanswered forum threads.* Section 5.5 alone would have saved
FrankSchlegel days, and Section 5.7 would have saved haozes from building the wrong thing.

### Guide 3 — "Entities, Spotlight, and Foundation Models: one index, three consumers"
*Integration. This is the one only we can write.*

1. `IndexedEntity` and `indexAppEntities` — minimal adoption
2. `@Property(indexingKey:)`, `customIndexingKey:`, `IndexedEntityQuery`
3. Lexical vs. semantic search over the same index
4. The two on-ramps to one index — App Intents vs. raw `CSSearchableItem`, with the comparison table
5. Consumer A: Siri entity resolution
6. Consumer B: `SpotlightSearchTool` -> `LanguageModelSession` — links straight into our
   existing `fm-ecosystem.md` PART C notes
7. The interop gap: `CSSearchableIndexDelegate` and entity-indexed content (open question)
8. Availability coupling and graceful degradation

*This guide resolves an UNVERIFIED question already sitting open in our corpus at
`fm-ecosystem.md:1400-1401`.* We are uniquely positioned to write it because we already have
deep `SpotlightSearchTool` notes; nobody writing about App Intents has those, and nobody
writing about Foundation Models has the entity-indexing detail.

### Not worth a separate guide
Query-protocol selection, `SnippetIntent`, and the new execution model (`LongRunningIntent`,
`ExecutionTargets`, `EntityCollection`, `@UnionValue`) are each a strong *section* but too thin
alone. Fold them into Guide 1.

### One caveat on all three
Every date/release label in this material is soft (Section 14, item 5), and one significant
documentation contradiction is unresolved (Section 5.6). Any guide should carry the
verified-working recipe as the headline and mark the architectural question as openly
unanswered by Apple — which is itself the honest and useful thing to tell a developer.

---

*Compiled from sources fetched 2026-07-27. Every API name, schema identifier and quotation
above traces to a page fetched during this session; items I could not confirm are marked
UNVERIFIED.*
