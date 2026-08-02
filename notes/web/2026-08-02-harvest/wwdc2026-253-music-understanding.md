# WWDC26 Session 253 — "Meet the Music Understanding framework"

**Harvested 2026-08-02** from `https://developer.apple.com/videos/play/wwdc2026/253/`
(direct WebFetch; Apple's published transcript + code-sample block, both complete).

> 🚨 **Before this harvest, the framework had no guide or captured-SDK coverage.** Greps for
> `Music Understanding`, `MusicUnderstanding`, and `MusicUnderstandingSession` returned **0 hits**
> across `guides/` and `notes/sdk-interfaces/`. This harvest adds the transcript and research note,
> but the **new on-device ML framework in the 2026 release** is still absent from Part 1's
> "Apple AI stack 2026 map." See §5 for where it belongs.
>
> ⚠️ **Provenance.** Code blocks below are copied from Apple's published "Code Samples" block on
> the session page (each carries Apple's own timestamp + chapter label). Prose is Apple's
> transcript. Nothing here is model-reconstructed. Several transcription or integration defects in
> Apple's own sample block are preserved verbatim and flagged inline.

Speaker: **Conner, Computational Music Team.**

---

## 1. What it is

On-device musical intelligence across **all Apple platforms**. Apple's framing:

> "It handles all the signal processing and model inference for you so you don't need any
> expertise in signal processing or machine learning to use it. And because it runs entirely
> on-device, the audio you analyze stays private and works offline."

**First-party adopter, named on stage:** Final Cut Pro — beat detection (rhythm + structure →
beat grid for edit alignment) and, on iPad, the montage feature (rhythm + pace + structure →
auto-sync clips to music).

**Sample app:** *Music Understanding Lab*, "available on developer.apple.com" — **not yet
downloaded into this corpus.** See §6.

## 2. The six analysis dimensions

| Dimension | What it yields | Result type |
|---|---|---|
| **Key** | tonic + mode, as time ranges | `KeyResult` |
| **Rhythm** | beat and bar timestamps, global BPM | `RhythmResult` |
| **Structure** | three-level hierarchy sections ⊃ segments ⊃ phrases | `StructureResult` |
| **Pace** | perceived speed/energy over time | `PaceResult` |
| **Instrument activity** | which instruments, when, how intensely | `InstrumentActivityResult` |
| **Loudness** | LUFS integrated/momentary/shortTerm + peak dB | `LoudnessResult` |

Apple's conceptual ladder, verbatim: beats → bars → phrases → segments → sections
("a chorus, verse, intro or bridge").

## 3. API surface (verbatim from Apple's code-sample block)

### 4:47 — Initialize the session *(chapter: Framework integration)*

```swift
import MusicUnderstanding

.fileImporter(isPresented: $isPresented, allowedContentTypes: [.audio]) { result in
    switch result {
    case .success(let url):
        let asset = AVURLAsset(url: url,
                               options: [AVURLAssetPreferPreciseDurationAndTimingKey : true])
        let session = try await MusicUnderstandingSession(asset: asset)
        let results = try await session.analyze()
    }
}
```

> ⚠️ **Integration erratum — the verbatim block above does not compile as written.** SwiftUI's
> single-file `fileImporter` completion is synchronous and delivers `Result<URL, Error>`, so the
> asynchronous session creation and analysis must run in a `Task`; the switch must also handle
> `.failure`. Because the selected URL may be outside the sandbox, balance
> `startAccessingSecurityScopedResource()` across the asynchronous work.

Corrected **derived** integration shape (not Apple's published block):

```swift illustrative
.fileImporter(isPresented: $isPresented, allowedContentTypes: [.audio]) { result in
    switch result {
    case .success(let url):
        Task {
            let isSecurityScoped = url.startAccessingSecurityScopedResource()
            defer {
                if isSecurityScoped {
                    url.stopAccessingSecurityScopedResource()
                }
            }

            do {
                let asset = AVURLAsset(
                    url: url,
                    options: [AVURLAssetPreferPreciseDurationAndTimingKey: true]
                )
                let session = try await MusicUnderstandingSession(asset: asset)
                let results = try await session.analyze()
                consume(results)
            } catch {
                handleImportError(error)
            }
        }
    case .failure(let error):
        handleImportError(error)
    }
}
```

> ⚠️ **Gotcha stated on stage:** "Be sure to set `PreferPreciseDurationAndTimingKey` to true to
> ensure the most accurate results." This is a silent-quality footgun — omitting it degrades
> results rather than erroring. **Candidate row for `guides/SILENT-FAILURES.md`.**

### 5:24 — `SessionResult`

```swift
public struct SessionResult: Codable, Sendable {
    public let instrumentActivity: InstrumentActivityResult?
    public let key: KeyResult?
    public let loudness: LoudnessResult?
    public let pace: PaceResult?
    public let rhythm: RhythmResult?
    public let structure: StructureResult?
}
```

> ⚠️ **Second silent-failure candidate.** Every field is optional. Apple: "When you use the
> general `analyze()` API, all results will be available. However, if you use the targeted
> `analyze(for:)` API, the framework will only return the results you asked for, and the rest
> will be **nil**." A caller who switches to `analyze(for:)` for performance and forgets to add
> a dimension gets `nil`, not an error.

### 5:53 / 5:58 — The two time-association types

```swift
public struct TimedValue<Value>: Codable, Equatable, Sendable
where Value: Codable & Equatable & Sendable {
    public let time: CMTime
    public let value: Value
}
```

```swift
public struct RangedValue<Value>: Codable, Equatable, Sendable
where Value: Codable & Equatable & Sendable {
    public let range: CMTimeRange
    public let value: Value
}
```

Note they are **nested under `MusicUnderstandingSession`** at every use site below
(`MusicUnderstandingSession.RangedValue<…>`), even though the declarations are shown unqualified.

### 6:27–6:59 — Key

```swift
public struct KeyResult: Codable, Sendable {
    public let ranges: [MusicUnderstandingSession.RangedValue<KeySignature]
}
```

> ⚠️ **Verbatim transcription artifact in Apple's own sample:** the generic bracket is unbalanced
> (`RangedValue<KeySignature]`). Correct spelling is almost certainly
> `[MusicUnderstandingSession.RangedValue<KeySignature>]`. Preserved as published; **do not copy
> into a compiled snippet without the fix** — `scripts/verify-snippets.py` would fail hard on it.

```swift
public struct KeySignature: Codable, Hashable, Sendable {
    public let tonic: Tonic
    public let mode: Mode
}
```

```swift
@frozen public enum Tonic: String, Codable, Hashable, Sendable {
    case aFlat, aSharp, a, bFlat, b, c, cSharp, d, dFlat, dSharp, eFlat, e, f, fSharp, g, gFlat, gSharp
}
```

> ⚠️ **17 cases, and the set is asymmetric** — `bSharp`, `cFlat`, `eSharp`, `fFlat` are absent
> (musically reasonable) but so is any spelling between `a`/`aSharp`/`bFlat` symmetry for
> `d`/`dSharp`/`eFlat` vs `g`/`gFlat`/`gSharp`. Note `@frozen` — the case set is committed ABI.

```swift
public enum Mode: String, Codable, Hashable, Sendable {
    case major, minor
}
```

### 7:16 — Rhythm

```swift
public struct RhythmResult: Codable, Sendable {
    public let beats: [CMTime]
    public let bars: [CMTime]
    public let beatsPerMinute: Float?
}
```

> ⚠️ **Third silent-failure candidate, stated explicitly on stage:** "if the framework hasn't
> processed enough audio to find at least two beats, the bpm will be set to **nil**." A
> documented `nil`-on-insufficient-input, not an error.

### 8:42 — Structure

```swift
public struct StructureResult: Codable, Sendable {
    public let sections: [CMTimeRange]
    public let segments: [CMTimeRange]
    public let phrases: [CMTimeRange]
}
```

### 9:26 — Pace

```swift
public struct PaceResult: Codable, Sendable {
    public let ranges: [MusicUnderstandingSession.RangedValue<Double>]
}
```

Pace is "an event per minute rate" (see the §14:47 sample — `60 / paceValue` gives seconds
per clip).

> ⚠️ **Dimensional erratum for the archived transcript:** its narration says the pace can be
> "divided by 60 seconds," which could be read as `paceValue / 60`. The published code sample has
> the unit-correct formula: **`secondsPerClip = 60 / paceValue`**.

### 10:13 — Instrument activity

```swift
public struct InstrumentActivityResult: Codable, Sendable {
    public let ranges: [Instrument: [CMTimeRange]]
    public let activity: [Instrument: [MusicUnderstandingSession.TimedValue<Float>]]
}
```

`ranges` = presence only; `activity` = intensity in **0…1**, "The closer the value is to 1, the
louder the instrument is in the mix." Apple names drums, bass, vocals as examples but **the
`Instrument` enum's case list was not shown** — 🔴 open.

### 11:45 — Loudness

```swift
public struct LoudnessResult: Codable, Sendable {
    public let integrated: MusicUnderstandingSession.TimedValue<Float>
    public let momentary: [MusicUnderstandingSession.TimedValue<Float>]
    public let shortTerm: [MusicUnderstandingSession.TimedValue<Float>]
    public let peak: MusicUnderstandingSession.TimedValue<Float>
}
```

Units and windows, from the narration:
- **LUFS** (Loudness Units Full Scale) — "the industry standard for modeling how the human ear
  perceives volume".
- `integrated` — one value, whole-song average.
- `momentary` — emitted **every 100 ms**, computed over a **400 ms** window → short sudden spikes.
- `shortTerm` — emitted every 100 ms, computed over a **3 s** window → smoothed trend.
- `peak` — absolute maximum, **measured in decibels**, not LUFS. (Mixed units inside one struct —
  worth a callout.)

### 12:48 / 12:55 — The streaming loudness API

```swift
public var loudnessResults: some AsyncSequence<LoudnessResult, any Error> & Sendable
```

```swift
let audioProvider = AudioProvider()
let session = MusicUnderstandingSession(audioProvider: audioProvider)
await withThrowingTaskGroup(of: Void.self) { taskGroup in
    group.addTask {
        for try await result in await session.loudnessResults {
            updateAudioLevel(result.momentary.value)
        }
    }

    group.addTask {
        try await session.analyze(for: [.loudness])
    }
}
```

> ⚠️ **Further verbatim artifacts in Apple's sample:** the throwing group call needs `try await`,
> the closure binds `taskGroup` but the body calls `group.addTask`, and `result.momentary` is
> declared as an **array** in `LoudnessResult` (11:45) yet is used here as a scalar
> (`.momentary.value`). The streaming element type is evidently *not* the same `LoudnessResult`
> shape as the batch one, or `momentary` is scalar in the streaming case. **Unresolved
> contradiction inside one Apple session.** 🔴 — preserve the archival block and resolve the
> result shape against the real SDK interface before writing a corrected guide snippet.

Note the two-task structure: **the consumer must be started before/alongside `analyze`**, because
values are delivered per 100 ms *during* analysis.

### 13:19 — `AudioProvider` (the custom-input path)

```swift
struct AudioProvider: AsyncSequence, AsyncIteratorProtocol {
   func makeAsyncIterator() -> Self {
        return self
    }

   mutating func next() async -> AVReadOnlyAudioPCMBuffer? {
        // Return the next audio buffer, or nil to signal completion
    }
}
```

Element type is **`AVReadOnlyAudioPCMBuffer`**. Apple: "When the AudioProvider has sent all audio
buffers, it must send a final **nil** to signal completion." → **a fourth silent-failure
candidate**: forget the terminating `nil` and `analyze()` presumably never returns.

### 13:55 — Everything is `Codable`

```swift
let session = try await MusicUnderstandingSession(asset: asset)
let results = try await session.analyze()

let encoder = JSONEncoder()
try encoder.encode(results)
```

### 14:47 — The pace→clip-count formula used by the Lab's video tile

```swift
let timePerClip = 60 / paceValue
```

## 4. Two initializer paths

1. `MusicUnderstandingSession(asset:)` — `async throws`, takes an `AVAsset`/`AVURLAsset`.
2. `MusicUnderstandingSession(audioProvider:)` — **not** shown as `throws`/`await` at 12:55,
   takes any `AsyncSequence` of `AVReadOnlyAudioPCMBuffer?`. Asymmetry is as published. 🟡

## 5. Where this belongs in the guide series

- **Part 1 / `01-apple-ai-stack-2026-map.md`** — the stack map omits an entire shipping
  on-device ML framework. This is the highest-priority edit from this file.
- **Part 16 (adjacent capabilities)** — a new reference guide, `06-music-understanding.md`,
  sits naturally beside `01-speech-analyzer-end-to-end.md`: same shape (on-device analyzer,
  `AsyncSequence` input, streaming results, `CMTime`-stamped output). The Speech guide's
  structure is the obvious template.
- **`guides/SILENT-FAILURES.md`** — four candidate rows identified above
  (`PreferPreciseDurationAndTimingKey`, `analyze(for:)` → `nil` fields, `beatsPerMinute` nil on
  <2 beats, missing terminating `nil` in the provider).

## 6. Follow-ups this file does NOT close

- 🔴 **`Instrument` enum case list** — never shown.
- 🔴 **The streaming-`LoudnessResult` contradiction** (§12:55 vs §11:45).
- 🔴 **Availability annotations** — no `@available` line appears anywhere in the session. Whether
  this is iOS 27.0+ across the board, and whether it reaches watchOS, is unattested. Apple says
  "all Apple platforms".
- 🔴 **Whether `MusicUnderstanding` is in the captured SDK interfaces** — it is not in
  `notes/sdk-interfaces/`, but that capture was scoped to FM/CoreAI/Speech/Evaluations, so this
  is *absence from our capture*, not absence from the SDK. **`scripts/dump-sdk-interfaces.sh`
  should be extended to capture it**, then this whole file gets SDK-verified.
- 🔴 **Sample app** — "Music Understanding Lab" on developer.apple.com not yet located/downloaded.
- Session **254 "Integrate MusicKit into your app"** is the companion and is also absent from
  the corpus.
