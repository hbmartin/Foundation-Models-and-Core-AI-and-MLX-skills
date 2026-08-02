# Five WWDC26 sessions absent from the corpus — 297, 375, 310, 256, 258

**Harvested 2026-08-02** by direct WebFetch of `developer.apple.com/videos/play/wwdc2026/<n>/`.
All five return **0 hits** when grepped for across `guides/`, `notes/`, `transcripts/`.

None of the five appears on `https://developer.apple.com/wwdc26/guides/machine-learning/` — that
page lists only the 18 sessions in the ML track. These five sit in the **Siri/App Intents, Media,
and Developer Tools tracks** while carrying material the guide series depends on. The lesson for
`notes/FRESHNESS-RUNBOOK.md`: the ML-track index is **not** a sufficient session inventory.

| # | Title | Why it matters here | Verdict |
|---|---|---|---|
| **297** | Best practices for integrating visual intelligence in your app | Part 16.3 (on-screen awareness, 13 🔴) | ⭐ **high value** |
| **310** | What's new in Shortcuts | Part 16.2 + Part 2 (a new *debugging tool* for entity→model data) | ⭐ **high value** |
| **375** | Create high-quality images using Image Playground | Part 1 stack map; a **deprecation** the corpus does not record | ⭐ **high value** |
| **256** | Discover generated subtitles and subtitle styles | Part 16.1 (Speech) | 🟡 useful **negative** result |
| **258** | What's new in Xcode 27 | Part 5/10 (Instruments lanes, Core AI Debugger) | 🔴 **negative** — does not close the gap |

---

## ⭐ 297 — Best practices for integrating visual intelligence in your app

Speaker: **David, ML engineer on System Experience.**

**What's new in the 2026 release, per the session:** "adding new capabilities like adding to
contacts, saving multiple calendar events, and medical device logging, as well as **bringing
Visual Intelligence to iPad and macOS**."

### The two integration directions (the framing Part 16 lacks)

1. **Your app → Visual Intelligence** via *Image Search* (App Intents + VisualIntelligence).
2. **Visual Intelligence → your app** via *system store integrations* — "**Events** can be read
   with **EventKit**, **contact information** with **Contacts**, and **medical device readings**
   with **HealthKit**. If your app already reads from the data stores in these frameworks,
   **Visual Intelligence becomes a new source of input automatically.**"

Direction 2 is a zero-code integration path and the corpus documents nothing about it.

### Code (verbatim, Apple's timestamps)

**3:21 — the entity**

```swift
// Define the content you want to return as an App Entity
import AppIntents

struct AlbumEntity: AppEntity {
    var id: String
    @Property var name: String
    @Property var artistName: String
    var coverArtData: Data
    
    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation( 
            title: "\(name)",
            subtitle: "\(artistName)",
            image: .init(data: coverArtData)
        )   
    }   
    
    static let defaultQuery = AlbumEntityQuery()
    
    static var typeDisplayRepresentation: TypeDisplayRepresentation { "Album" }
}   

struct AlbumEntityQuery: EntityQuery {
    @Dependency var catalog: AlbumCatalog
    func entities(for identifiers: [String]) async throws -> [AlbumEntity] {
        catalog.albums(for: identifiers)
    }
}
```

**5:39 — the query. `IntentValueQuery` + `SemanticContentDescriptor`**

```swift
// Adopt IntentValueQuery to return visual search results
import AppIntents
import VisualIntelligence

struct SearchHandler: IntentValueQuery {
    @Dependency var catalog: AlbumCatalog
    @Dependency var concertFinder: ConcertFinder
    
    func values(for input: SemanticContentDescriptor) async throws -> [VisualSearchResult] {
        guard let pixelBuffer = input.pixelBuffer else {
            return []
        }   
        
        let albums = try await catalog.search(matching: pixelBuffer)
        
        return albums.map { VisualSearchResult.album($0) }
    }
}
```

**6:24 / 6:45 — on-device matching with Vision feature prints**

```swift
// Build a catalog of albums with precomputed feature prints
import Vision

@Observable
class AlbumCatalog {
    static let shared = AlbumCatalog()
    
    struct CatalogEntry: Sendable {
        let album: AlbumEntity
        let featurePrint: FeaturePrintObservation
    }   
    
    private(set) var entries: [CatalogEntry] = []
    
    private func generateFeaturePrint(
        for image: CGImage
    ) async throws -> FeaturePrintObservation {
        let request = GenerateImageFeaturePrintRequest()
        let result = try await request.perform(on: image)
        return result
    }
}
```

```swift
// Search the catalog for albums matching the captured image
func search(matching pixelBuffer: CVReadOnlyPixelBuffer, limit: Int = 10, maxDistance: Double = 1.0) async throws ->
[AlbumEntity] {
    var cgImage: CGImage?
    _ = pixelBuffer.withUnsafeBuffer { VTCreateCGImageFromCVPixelBuffer($0, options: nil, imageOut: &cgImage) }
    guard let cgImage else { return [] }
    
    let queryPrint = try await generateFeaturePrint(for: cgImage)
    
    return try entries.compactMap { entry -> (album: AlbumEntity, distance: Double)? in
        let distance = try queryPrint.distance(to: entry.featurePrint)
        guard distance <= maxDistance else { return nil }
        return (entry.album, distance)
    }   
    .sorted { $0.distance < $1.distance }
    .prefix(limit)
    .map { $0.album }
}
```

Note **`CVReadOnlyPixelBuffer`** with a `withUnsafeBuffer` accessor — the 2026 read-only pixel
buffer type, matching the `CMReadySampleBuffer<CMReadOnlyDataBlockBuffer>` pattern that appears in
the Speech 27.0 interface. Same platform-wide move to read-only buffer wrappers.

**8:27 — `OpenIntent`**

```swift
// Create an open intent to land users on the right screen
import AppIntents

struct OpenAlbumIntent: OpenIntent {
    static let title: LocalizedStringResource = "Open Album"
    
    @Parameter(title: "Album")
    var target: AlbumEntity
    
    @Dependency var appState: AppState
    
    func perform() async throws -> some IntentResult {
        await appState.openAlbum(id: target.id)
        return .result()
    }
}
```

**12:05 / 12:18 — `@UnionValue`, and the constraint that forces it**

> "**Since our app can only have one `IntentValueQuery` that accepts a `SemanticContentDescriptor`**,
> I'll define a `@UnionValue` enum with a case for each entity type."

```swift
// Use UnionValue to return multiple visual search result types
@UnionValue
enum VisualSearchResult {
    case album(AlbumEntity)
    case concert(ConcertEntity)
}   

struct OpenConcertIntent: OpenIntent {
    static let title: LocalizedStringResource = "Open Concert"
    
    @Parameter(title: "Concert")
    var target: ConcertEntity
    
    @Dependency var appState: AppState
    
    func perform() async throws -> some IntentResult {
        await appState.openConcert(id: target.id)
        return .result()
    }
}
```

```swift
// Expand the IntentValueQuery to return the UnionValue
struct SearchHandler: IntentValueQuery {
    @Dependency var catalog: AlbumCatalog
    @Dependency var concertFinder: ConcertFinder
    
    func values(for input: SemanticContentDescriptor) async throws -> [VisualSearchResult] {
        guard let pixelBuffer = input.pixelBuffer else {
            return []
        }   
        
        let albums = try await catalog.search(matching: pixelBuffer)
        
        let artists = albums.map { $0.artistName }
        
        let concerts = await concertFinder.findNearby(byArtists: artists)

        return albums.map { VisualSearchResult.album($0) }
            + concerts.map { VisualSearchResult.concert($0) }
    }
}
```

**13:13 — the `.visualIntelligence.semanticContentSearch` schema**

```swift
// Provide a link to in-app search
@AppIntent(schema: .visualIntelligence.semanticContentSearch)
struct SemanticContentSearchIntent: AppIntent {
    static let title: LocalizedStringResource = "Search in app"
    static let openAppWhenRun: Bool = true
    
    var semanticContent: SemanticContentDescriptor
    @Dependency var catalog: AlbumCatalog
    @Dependency var concertFinder: ConcertFinder
    @Dependency var appState: AppState
    
    func perform() async throws -> some IntentResult {
        guard let pixelBuffer = semanticContent.pixelBuffer else { return .result() }
        let albums = try await catalog.search(matching: pixelBuffer)
        let artists = albums.map { $0.artistName }
        let concerts = await concertFinder.findNearby(byArtists: artists)
        await appState.openSearch(albums: albums, concerts: concerts)
        return .result()
    }   
}
```

> ⚠️ **Cross-check required.** Part 16.2 (`02-app-schema-domains.md`, 18 🔴) enumerates the schema
> domains. **`.visualIntelligence.semanticContentSearch` must be checked against that
> enumeration** — if the count in `notes/web/app-intents-siri-schemas.md` §3.5 ("Counting the
> surface") omits a `visualIntelligence` domain, the count is wrong.

**15:24–15:44 — the EventKit side (direction 2)**

```swift
// Request calendar access and fetch upcoming concerts
import EventKit

@Observable
class UpcomingConcertManager {
    private let eventStore = EKEventStore()
    var upcomingConcerts: [EKEvent] = []
    var authorizationStatus: EKAuthorizationStatus = .notDetermined
    
    func requestAccessAndFetch() async throws {
        let granted = try await eventStore.requestFullAccessToEvents()
        guard granted else {
            authorizationStatus = .denied
            return
        }   
        authorizationStatus = .fullAccess
        await fetchUpcomingConcerts()

        // ...
    }
}
```

```swift
// Observe newly created events
@Observable
class UpcomingConcertManager {
    // ...

    func requestAccessAndFetch() async throws {
        // ...

        for await _ in NotificationCenter.default
            .notifications(
                named: .EKEventStoreChanged
            ) {
            await fetchUpcomingConcerts()
        }
    }
}
```

### Behavioural rules stated on stage (guide-worthy)

- **Display budget:** "you get about **three lines of text** for a title and subtitle, as well as a
  thumbnail image."
- **Thumbnail sizing:** serve a thumbnail-sized image, not the full-resolution asset. "if you only
  return one result, keep in mind that this image will take up the **full width** of the results
  sheet."
- **Empty results are legitimate:** "If you don't find any good matches, you can return an empty
  array. **The system will handle displaying an empty response.**"
- **Ordering among apps is not yours:** "your app appears here alongside other adopting apps.
  **The system decides the ordering** based on which Image Search providers are available."
- **`OpenIntent` must be cheap:** "This method runs **as the app comes to the foreground**, so do
  your navigation and save any heavy loading for after the view appears." → silent-failure
  candidate (a heavy `perform` degrades launch, it does not error).
- **Platform asymmetry:** iOS entry point is the camera; **macOS/iPad is screenshots**. "on Mac,
  the input pixel buffer can be **much larger** than what you'd encounter on iPhone. Consider if
  resizing is necessary." → a real portability footgun for Part 16.3.
- **Reuse, don't duplicate:** "If you already have an `OpenIntent` for your entity … you can reuse
  it here too."

---

## ⭐ 375 — Create high-quality images using Image Playground

Speaker: **Antonio, Image Playground team.**

### 🚨 The finding that matters most: a deprecation the corpus does not record

> "Moving the models to Private Cloud Compute also meant rethinking the API. **`ImageCreator`, the
> non-UI API for generating images directly in your code, is deprecated.** Everything is now
> available through a new API with greater image quality, built-in privacy, and a full experience
> people already know how to use."

**This belongs in Part 17 (`01-what-changed-checklist.md`) as a 2026 deprecation**, alongside the
adapter sunset and the `GenerationError` deprecation. It is also a *capability regression* worth
flagging plainly: there is **no longer a headless image-generation API** — the replacement is
sheet-based UI (`.imagePlaygroundSheet` / `ImagePlaygroundViewController`), so programmatic
batch generation is no longer possible on this path.

### Architecture facts

- **All image generation now runs on Private Cloud Compute**, not on-device: "All of this runs on
  Private Cloud Compute, Apple's privacy-preserving cloud infrastructure. Your data is never
  stored or shared, even with Apple." Cross-reference Part 4.1.
- **Usage limits are system-managed, not developer-managed:** "Image Playground has a usage limit
  because it relies on powerful server models. **Increased access is available with most iCloud+
  subscription plans.** … The system manages usage limits on behalf of your users, **you never
  need to build any usage-related UI.**" Contrast with the FM PCC quota story in Part 4, where the
  developer *does* see `QuotaUsage`.
- **Gating is one environment value:** `@Environment(\.supportsImageGeneration)` — true only when
  "the device has the capability, the current language and region are supported, and the user has
  it enabled." **"No entitlement, no extra capability check."** Directly relevant to Part 1.2
  (platform and version gating, 17 🔴).
- **Third-party providers are surfaced by the system:** `ImagePlaygroundStyle.externalProvider` is
  "an opt-in style that surfaces whatever third-party provider the person has configured in
  Settings, **ChatGPT, for example**." If unconfigured, "the system handles its setup, no check
  required on your side." This is a second, independent instance of the 2026 "Apple frameworks
  broker third-party models" pattern that Part 4 documents for `LanguageModel`.

### API surface (verbatim samples, abridged to the distinct shapes)

**5:28 — the modifier signature**

```swift
func imagePlaygroundSheet(
    isPresented: Binding<Bool>,
    concepts: [ImagePlaygroundConcept] = [],
    sourceImage: Image? = nil,
    onCompletion: @escaping (URL) -> Void,
    onCancellation: (() -> Void)? = nil
) -> some View
```

> ⚠️ **Silent-failure candidate, stated on stage:** "the completion closure receives a URL to the
> generated file. **That URL points to a temporary location inside your app container, save it
> elsewhere before the session ends.**"

**6:29 / 7:42 — concepts**

```swift
var concepts: [ImagePlaygroundConcept] {
    [
        .text(card.theme),
        .extracted(from: card.message, title: card.theme),
    ]
}
```

```swift
@State private var drawing = PKDrawing()

var concepts: [ImagePlaygroundConcept] {
    var result: [ImagePlaygroundConcept] = [
        .text(card.theme),
        .extracted(from: card.message)
    ]
    if !drawing.strokes.isEmpty {
        result.append(.drawing(drawing))
    }
    return result
}
```

Three factories: `.text(_:)` (a direct description), `.extracted(from:title:)` ("takes longer text
and lets the system pull out the most relevant ideas"), `.drawing(_:)` (a PencilKit `PKDrawing`,
treated as "a visual suggestion").

**8:06 — UIKit/AppKit**

```swift
func presentViewController() {
    let viewController = ImagePlaygroundViewController()
    viewController.concepts = [
        .text(card.theme),
        .extracted(from: card.message)
    ]
    viewController.delegate = self
    present(viewController, animated: true)
}

func imagePlaygroundViewController(
    _ viewController: ImagePlaygroundViewController,
    didCreateImageAt url: URL
) {
    var updated = card
    store.saveImage(url, for: &updated)
    dismiss(animated: true)
}
```

**9:02 / 9:39 / 10:27 / 12:01 — options and styles**

```swift
var options: ImagePlaygroundOptions {
    var options = ImagePlaygroundOptions()
    options.sizeSpecification = .closest(to: card.format.size)
    options.personalization = .disabled
    return options
}
```

```swift
.imagePlaygroundOptions(options)
.imagePlaygroundGenerationStyle(
    pendingStylePreset.defaultStyle,
    in: pendingStylePreset.allowedStyles + [.externalProvider]
)
```

- `sizeSpecification = .closest(to: CGSize)` — "The model picks the **closest supported
  resolution** to the size you ask for."
- `imagePlaygroundGenerationStyle(_:in:)` takes a default style **and** an allow-list; "**If you
  pass a single style in the allowed list, the picker locks to that style.**"
- `ImagePlaygroundStyle` values named: `illustration`, `sketch`, `animation`, `emoji`,
  `externalProvider`.
- `personalization` is **enabled by default**; `.disabled` removes "the people picker and name
  detection … from the sheet entirely."

**11:02 — the Genmoji branch, which returns a different type**

```swift
Color.clear
    .imagePlaygroundSheet(
        isPresented: $showingIconPlayground,
        concepts: concepts,
        onCompletion: { _ in
        } ,
        onAdaptiveImageGlyphCreation: { glyph in
            var updatedCard = card
            store.saveIcon(glyph, for: &updatedCard)
        }
    )
    .imagePlaygroundGenerationStyle(.emoji, in: [.emoji])
```

> ⚠️ **Sharp API edge:** with `.emoji` active "the sheet fires a **separate completion**,
> `onAdaptiveImageGlyphCreation`, and hands you an **`NSAdaptiveImageGlyph` instead of a URL**."
> A caller who wires only `onCompletion` and selects the emoji style gets **nothing** — no URL, no
> error. **Strong `SILENT-FAILURES.md` candidate.** Note the sample's `onCompletion: { _ in }`
> empty body, and the `Color.clear` host view.

**12:32 — availability**

```swift
@Environment(\.supportsImageGeneration)
private var supportsImageGeneration

var body: some View {
    NavigationLink(card.recipient) {
        if supportsImageGeneration {
            CardEditorView(card: card)
        } else {
            CardPickerView(card: card)
        }
    }
}
```

---

## ⭐ 310 — What's new in Shortcuts

### The find: **Model Transcript Inspector** — a debugging tool for entity→model data

The *Use Model* action gains "a new debugging feature: **Model Transcript Inspector** — Inspect
exactly what data is passed to the model from App Intent entities. View structured representation
of entities in **raw format**. Helps identify **missing properties** that models need for accurate
results."

**Why this is valuable here.** Part 16 and Part 2 both have to answer "what does the model actually
see when my entity is handed to it?" — and the corpus answers it by reasoning from
`displayRepresentation` and `@Property` annotations. This is a **shipped inspector that shows the
ground truth**, and it is usable without writing any code. It should be named in Part 16.2 and in
Part 2.4 as the empirical check, and added to `notes/NEXT-BETA-CHECKLIST.md` as something to run.

The associated practice, stated in the session: "**Expose relevant properties on App Entities**
(like ingredients list) so models have sufficient context for accurate decisions."

### The other find: iCloud-synced entities need stable identifiers

Shortcuts gains **Storage** (Get / Set, global values, syncs across devices via iCloud, "Store any
Shortcuts data type, **including App Entities**").

> **Critical implementation note from the session:** "For App Entities stored with iCloud sync, use
> a **stable, device-consistent identifier** (e.g., database row ID) rather than device-specific
> values. This ensures the entity is recognized identically across all devices."

This is the **same requirement `SyncableEntity` encodes** (Part 16 already tracks `SyncableEntity`
in 5 guides). Session 310 states the failure mode in user-visible terms and from a second,
independent direction — worth citing together.

Sample entity, verbatim:

```swift
// MARK: - Soup Entity
import AppIntents

struct SoupEntity: AppEntity, Identifiable {
    static var typeDisplayRepresentation = TypeDisplayRepresentation(
        name: "Soup",
        numericFormat: "\(placeholder: .int) soups"
    )
    static var defaultQuery = SoupEntityQuery()
    
    var id: Soup.ID  // Stable identifier from database
    
    @Property var name: String
    
    @Property(title: "Available Today")
    var isAvailableToday: Bool
    
    @Property(title: "Ingredients")
    var ingredients: String
    
    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(name)", subtitle: SoupStore.description(for: id))
    }
}
```

Note `TypeDisplayRepresentation(name:numericFormat:)` with the `"\(placeholder: .int) soups"`
interpolation — check this spelling against Part 16.2's enumeration.

Also new: three automation types — **screenshot saved**, **external keyboard connect/disconnect**,
**notification received from a specific app with keyword filtering**. And the *Use Model* action
now has "access to latest Apple Intelligence models **with web retrieval capabilities**" — a
capability the corpus does not attribute to any FM API surface. 🔴 worth chasing: is web retrieval
Shortcuts-only, or is there a developer-facing equivalent?

---

## 🟡 256 — Discover generated subtitles and subtitle styles (a useful negative)

**Question asked:** does Apple's system subtitle generation expose or use SpeechAnalyzer /
SpeechTranscriber in a way the Speech guide should document?

**Answer: no.** The session says the audio "goes into the **on-device Speech-To-Text model**" and
that "**you don't need to implement anything** to turn on generated subtitles. They're available
automatically during video playback." The only API shown is subtitle *styling*:

```swift
import AVFoundation
import MediaAccessibility

MACaptionAppearanceCopyProfileIDs()
playerLayer.setCaptionPreviewProfileID(subtitleStyleProfileID, position: .zero, text: nil)
playerLayer.stopShowingCaptionPreview()
MACaptionAppearanceSetActiveProfileID(subtitleStyleProfileID)
```

**Use in the guides:** one line in Part 16.1 noting that the system's own generated-subtitles
feature is *not* built on a public Speech API surface and gives developers no additional
transcription entry point. This forecloses a plausible reader assumption; it does not close any
existing 🔴.

---

## 🔴 258 — What's new in Xcode 27 (does NOT close the Instruments gap, but is not empty)

> ⚠️ **Correction to this file's first draft.** The initial pass fetched only a truncated summary
> of 258 and concluded it had "no Instruments content". **That was wrong.** The full transcript
> (now at `transcripts/wwdc2026-258.txt`, 322 lines) contains a substantial Instruments and
> Organizer section. What remains true is the narrower claim below: it does not close the
> *lane-names* gap.

**Checked specifically against `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 3 (Instruments lane
names) and the Core AI Debugger question.**

**It does not mention:** Instruments templates for AI workloads, the Foundation Models or Core AI
instrument lanes, the Core AI Debugger, or any Core-AI-specific tooling. **Item 3 stands
unchanged** — the lane names still require one manual GUI recording against the booted iOS 27
simulator on this machine. Record this negative so the next agent does not re-fetch 258 hoping
for it.

**What 258 *does* contain that the guide series can use:**

- ⭐ **Instruments "Top Functions" is new in Xcode 27.** "Top Functions is perfect for finding
  performance problems that arise due to expensive operations that are performed many times."
  The worked example selects a time range in a CPU profile, presses Top Functions, and reads the
  hot symbol straight off the list. **Relevant to Part 10.2 (debugging and profiling, 11 🔴) and
  Part 5.1** — it is a generic Instruments capability that applies to inference workloads, and
  the corpus does not mention it. Also named: comparing performance runs across recordings, and
  "processor trace".
- **Organizer gains four things**, of which two matter for Part 15.2 (memory, thermals, honest
  benchmarking): a new **Storage metric** (breaks down documents, data, and **binary size**,
  "since binary size impacts cellular downloads and launch time" — directly relevant to shipping
  models inside an app bundle, Part 15.1), and an expanded **hitches metric** that "surfaces
  issues in more places than scrolling". Plus **Metric Goals** (hang rate, disk writes, battery,
  storage, hitches — calibrated against similar apps *and* your own historical baselines) and
  **Generate Recommendations**, which runs a coding agent over the diagnostic data.
- Coding-agent workflow: conversations as editor panes, a **`/plan`** command that gathers context
  and "can kick off sub-agents to work in parallel", a coding-assistant sidebar, agent-driven
  localisation, and **Device Hub** for driving simulators and physical devices from a Mac window.
  Out of scope for the guide content, noted for completeness.

(One adjacent item worth noting for the Xcode-side story: the SwiftUI group lab 8120 mentions
"the new **skills** shipping with Xcode [that] give the coding agent accurate insight into current
APIs … and **you can export them for use in other agentic systems**" — relevant to this repo's own
`skills/` directory and `scripts/build-skills.sh`, though not to the guide content.)
