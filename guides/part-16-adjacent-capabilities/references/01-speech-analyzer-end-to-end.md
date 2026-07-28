# SpeechAnalyzer: live transcription, assets, and custom vocabulary

**Part 16 · Adjacent capabilities · Reference 01**

**Version floor: iOS 27.0 / iPadOS 27.0 / macOS 27.0 / visionOS 27.0 / tvOS 27.0, Xcode 27**
for the new input-sequence providers that are the headline change this year
(`CaptureInputSequenceProvider`, `AssetInputSequenceProvider`, `AnalyzerInputConverter` — all
marked `iOS 27.0+ Beta … tvOS 27.0+ Beta, visionOS 27.0+ Beta`). The pipeline they feed is
**older**: `SpeechAnalyzer`, `SpeechTranscriber`, `DictationTranscriber`, `SpeechDetector`,
`AnalyzerInput` and `AssetInventory` are all **iOS 26.0 / macOS 26.0**, and the custom-vocabulary
layer (`SFCustomLanguageModelData`, `SFSpeechLanguageModel`) is **iOS 17.0 / macOS 14.0** and has
not moved since. So this guide spans three availability generations in one file, and every symbol
below is tagged with the earliest OS that has it. Getting that wrong is the fastest way to ship a
build that compiles on your Mac and refuses to link for a customer.

⚠️ **Two things you probably came here for do not exist. Read §1 before anything else.** One is a
text-to-speech API. The other is a sample project demonstrating the 2026 APIs.

---

## Evidence markers used in this guide

> ✅ **VERIFIED** — quoted from an Apple documentation page or a compiling Apple sample project
> that we read this session. The citation follows the claim.
>
> 🟡 **RECONSTRUCTED** — the concept is attested in an Apple source, but the exact spelling, type
> or default is inferred. Treat the shape as right and the identifier as provisional.
>
> 🔴 **GAP** — we could not verify it and are saying so rather than inventing it. Every gap box
> names what is unknown, what would resolve it, and a safe default.

The **strongest** evidence class in this guide is Apple's own documentation article
*"Recognizing speech in live audio"* (`/documentation/speech/recognizing-speech-in-live-audio`,
fetched 2026-07-27), which is marked **iOS 27.0+ Beta, iPadOS 27.0+ Beta, Mac Catalyst 27.0+ Beta,
Xcode 27.0+ Beta** and walks through the SpokenWord sample line by line. Nearly every code
fragment in §2–§11 is quoted from it or from the framework reference pages it links.

The **weakest** thing you can lean on here is the downloadable sample ZIP — see §1.2.

---

## What this covers

`SpeechAnalyzer` is the 2026 speech-to-text stack: an actor that owns a set of analysis
**modules**, accepts a single asynchronous sequence of time-coded audio, and hands each module's
output back to you as its own `AsyncSequence`. Nothing about it looks like `SFSpeechRecognizer`.
There is no delegate, no recognition *request* object, no authorization dance in the common path,
and — critically — **no accumulated transcript**. The framework gives you a stream of results, each
stamped with the range of audio it describes, and expects *you* to assemble the document.

This guide covers:

- **§1 — Two warnings.** No TTS API; the sample project is a WWDC25 leftover.
- **§2 — The shape of the pipeline.** Analyzer, modules, results; Apple's eight-step canonical
  flow; what "finished" actually means.
- **§3 — Choosing a transcriber.** `SpeechTranscriber` vs `DictationTranscriber`, the platform
  matrix, and the one-line rule Apple gives for falling back.
- **§4 — Presets and content hints.** Both full preset matrices, how to modify a preset without
  breaking it, and `customizedLanguage(modelConfiguration:)`.
- **§5 — Assets.** Why `AssetInventory` exists, the reservation quota, and the three things that
  break silently if you skip it.
- **§6 — Input, the headline change.** `CaptureInputSequenceProvider` replaces the hand-installed
  audio-engine tap. Complete code for microphone capture, file playback, and the hand-rolled
  fallback with `AnalyzerInputConverter`.
- **§7 — Running the analysis.** `analyzeSequence(_:)` → last audio time → `finalizeAndFinish(through:)`,
  and why terminating your input stream is *not* how you stop.
- **§8 — Result merging.** The subtle part. Two documented strategies, the trade between them, and
  the attribute-option trap that makes the first one silently no-op.
- **§9 — The cancellation shield.** ⚠️ The signature silent failure of this API: the display task
  must be shielded from cancellation or you lose the last words of every recording.
- **§10 — A complete worked example**, assembled from Apple's fragments with every gap marked.
- **§11 — Custom vocabulary.** The `SFCustomLanguageModelData` result-builder DSL, the offline
  build step, and `prepareCustomLanguageModel(for:configuration:)`.
- **§12 — `SpeechDetector`**, and why its `Result` stream is not what you think.
- **§13 — Resource limits, model retention, prewarming.**
- **§14 — The other path.** `apple/coreai-models` ships a `CoreAISpeech` product with a Whisper
  encoder/decoder on Core AI. Completely different trade-offs. Cross-links Part 7.
- **§15/§16 — Declared gaps and a silent-failure checklist.**

## What this does *not* cover

- **Text-to-speech / speech synthesis.** There is no new API (§1.1). AVFoundation's speech
  synthesis is out of scope for this series.
- **The legacy `SFSpeechRecognizer` stack** (`SFSpeechAudioBufferRecognitionRequest`,
  `SFSpeechRecognitionTask`, `SFTranscription`, `SFVoiceAnalytics`, …). It still ships and is
  still documented. If you are maintaining it, the only 2026-relevant facts are that
  `DictationTranscriber` uses *the same models* as on-device `SFSpeechRecognizer`, and that the
  custom-vocabulary types are shared between the two stacks.
- **Speaker diarization, translation, or audio classification.** Not in the Speech framework.
- **Feeding transcripts into Foundation Models.** That is a `LanguageModelSession` problem;
  see [Part 2](../../part-02-foundation-models-everyday-api/). The one thing worth saying here is
  that transcript results are `AttributedString`, and you will want
  `String(result.text.characters)` before you put anything in a `Prompt`.

## What you need

- **A physical device running iOS 27 or iPadOS 27.** ✅ VERIFIED — Apple's article carries a
  standing note: *"The sample app doesn't run in the iOS Simulator, so you need to run it on a
  physical device with iOS or iPadOS 27 or later."* This is not a sample-code quirk you can code
  around; audio capture and the speech assets both want real hardware.
- **Xcode 27.** The 2026 input providers are `iOS 27.0+ Beta` symbols; the Xcode 26 SDK does not
  have them.
- **Microphone permission** and network access for the first asset download.
- **`import Speech`** — the analyzer, the modules, the providers and the custom-vocabulary types
  are all in one framework. You will also touch `AVFoundation` (capture device and session),
  `CoreMedia` (`CMTime`) and `Foundation` (`AttributedString` and the speech attribute scopes).

🔴 **GAP — the macOS availability of the 2026 sample article.** The page for *"Recognizing speech
in live audio"* lists **iOS 27.0+, iPadOS 27.0+, Mac Catalyst 27.0+, Xcode 27.0+ — and no native
macOS entry**, even though `CaptureInputSequenceProvider` itself is documented for macOS 27. The
most likely explanation is that the *sample project* is iOS-only and the availability line
describes the project rather than the API. We cannot confirm that from the page alone. **Safe
default:** treat the API as available on macOS 27 (its own reference page says so) but expect to
write your own AVCaptureSession plumbing on macOS rather than lifting the sample wholesale.

---

## Contents

1. [Two warnings before you write any code](#1-two-warnings-before-you-write-any-code)
2. [The shape of the pipeline](#2-the-shape-of-the-pipeline)
3. [Choosing a transcriber](#3-choosing-a-transcriber)
4. [Presets, options, and content hints](#4-presets-options-and-content-hints)
5. [Assets: `AssetInventory` and the reservation quota](#5-assets-assetinventory-and-the-reservation-quota)
6. [Input: `CaptureInputSequenceProvider` and friends](#6-input-captureinputsequenceprovider-and-friends)
7. [Running the analysis](#7-running-the-analysis)
8. [Result merging: the subtle part](#8-result-merging-the-subtle-part)
9. [⚠️ The cancellation shield](#9--the-cancellation-shield)
10. [A complete worked example](#10-a-complete-worked-example)
11. [Custom vocabulary and custom language models](#11-custom-vocabulary-and-custom-language-models)
12. [`SpeechDetector`: gating on voice activity](#12-speechdetector-gating-on-voice-activity)
13. [Resource limits, model retention, prewarming](#13-resource-limits-model-retention-prewarming)
14. [The other path: `CoreAISpeech` and Whisper on Core AI](#14-the-other-path-coreaispeech-and-whisper-on-core-ai)
15. [Declared gaps](#15-declared-gaps)
16. [Silent-failure checklist](#16-silent-failure-checklist)
17. [Sources](#17-sources)

---

## 1. Two warnings before you write any code

Most guides open with the happy path. This one cannot, because two of the most common reasons a
developer opens a 2026 Speech guide lead nowhere, and finding that out on page nine is worse than
finding it out on page one.

### 1.1 There is no new text-to-speech API

The WWDC26 keynote advertised speech *generation* on the second-generation on-device model. Craig
Federighi, at **30m:20s** of the keynote, described an "even more powerful version of our on-device
model" that "lets supported products understand **and generate** speech." Developers watched that,
went looking for the API, and found nothing.

They asked. The answer, from an Apple employee on Developer Forums **thread 834149** ("TTS Advanced
Speech Generation: Expressive voices", opened 2026-06-12), is unambiguous:

> ✅ **VERIFIED** — Apple staff reply, forum thread 834149, verbatim:
>
> *"The short answer is no. No new API has been released specific to that model. Though of course
> you still have the older existing speech synthesis APIs in AV Foundation
> https://developer.apple.com/documentation/avfoundation/speech-synthesis"*

A second thread — **832868**, "Speech generation by the new Foundation Model", which explicitly
cites the keynote timestamp — sat with **zero replies**.

**The conclusion to carry away:** the advanced speech-generation capability of the second-generation
on-device model is **not exposed to third-party developers as of July 2026**. If you need your app
to speak, you use the same AVFoundation speech-synthesis API you would have used in 2019. Nothing
in the Speech framework, nothing in Foundation Models, and nothing in Core AI gives you the
keynote's voice.

This matters for planning, not just for expectations. If your product brief says "conversational
voice assistant", the speech-*in* half of that is genuinely new and genuinely good, and the
speech-*out* half is unchanged. Budget accordingly, and do not build a roadmap on a WWDC keynote
sentence that no shipping symbol backs.

> 🔴 **GAP — whether an API is coming.** Apple's reply says "no new API has been released", not
> "no API will be released". Nothing in our corpus indicates a timeline. **Safe default:** ship on
> AVFoundation speech synthesis, and structure your audio-output layer behind a protocol of your
> own so a future replacement is a one-file change.

### 1.2 The SpeechAnalyzer sample project is a WWDC25 leftover

The Speech framework's documentation index lists two sample-code pages. They are not equally
useful, and one of them is a trap.

| Page | Availability line on the page | What it actually is |
|---|---|---|
| *Bringing advanced speech-to-text capabilities to your app* | `iOS 26.0+, iPadOS 26.0+, Mac Catalyst 26.0+, macOS 26.0+, Xcode 26.0+` | ⚠️ The **WWDC25** sample. Downloadable. Stale. |
| *Recognizing speech in live audio* | `iOS 27.0+ Beta, iPadOS 27.0+ Beta, Mac Catalyst 27.0+ Beta, Xcode 27.0+ Beta` | The **2026** article. Describes SpokenWord. This is the good one. |

The first page's own overview note gives the game away:

> ✅ **VERIFIED** — from `/documentation/speech/bringing-advanced-speech-to-text-capabilities-to-your-app`,
> verbatim:
>
> *"This sample code project is associated with **WWDC25 session 277**: Bring advanced speech-to-text
> to your app with SpeechAnalyzer."*

We downloaded and read that ZIP (`BringingAdvancedSpeechToTextCapabilitiesToYourApp.zip`, 55,630
bytes, 8 Swift files, project name `SwiftTranscriptionSampleApp`). Its build settings say
`IPHONEOS_DEPLOYMENT_TARGET = 26.0`, `MACOSX_DEPLOYMENT_TARGET = 26.0`, `SWIFT_VERSION = 5.0`. The
git history inside the archive is **two commits**: `Initial release for WWDC25` and
`Updated to latest SDK`. It was never refreshed for WWDC26.

An exhaustive grep across all eight Swift files produced this table, which is the single most
important orientation fact in this guide:

| Symbol this guide teaches | Present in the downloadable sample? |
|---|---|
| `SpeechAnalyzer` | ✅ yes |
| `SpeechTranscriber` | ✅ yes |
| `AssetInventory` (`assetInstallationRequest(supporting:)`, `reservedLocales`, `release(reservedLocale:)`) | ✅ yes |
| `AnalyzerInput` | ✅ yes |
| **`DictationTranscriber`** | ❌ **absent** |
| **`CaptureInputSequenceProvider`** | ❌ **absent** |
| **`AssetInputSequenceProvider`** | ❌ **absent** |
| **`AnalyzerInputConverter`** | ❌ **absent** |
| **`SFCustomLanguageModelData`** | ❌ **absent** |
| **the `datagenerator` CLI** | ❌ **absent** — the project has no command-line target at all |

Meanwhile the *2026* article — *"Recognizing speech in live audio"* — describes a **different**
app called SpokenWord that uses every one of those symbols, and includes a `datagenerator`
command-line utility and a pre-built `CustomLMData (en_US).bin`. We have the article. We do not
have that project's ZIP, and the framework index does not currently point at a downloadable
archive for it that we could retrieve.

**What this means practically.** Everything in §6, §9 and §11 of this guide is sourced from Apple's
prose and code fragments in the 2026 article, plus the individual reference pages for each symbol.
That is documentation-grade evidence, which is good — but it is **not** compiling-sample-grade
evidence, which is better. Where a fragment is quoted verbatim from the article, this guide says
so. Where a line had to be assembled to make a complete listing, it is marked 🟡, and §15 collects
every such assembly in one place.

> ⚠️ **Do not "verify" the 2026 API by opening the downloadable sample.** It will compile, it will
> run, and it will teach you the iOS 26 pattern — a hand-built `AsyncStream<AnalyzerInput>`, a
> manually installed audio tap, `SpeechTranscriber` with no content hints. Every one of those is
> still supported. None of them is what changed this year.

### 1.3 What *did* change in 2026

The Speech framework's entire published changelog for the year is two bullets. Here it is,
in full:

> ✅ **VERIFIED** — `/documentation/updates/speech`, "June 2026" section, verbatim and complete:
>
> - *"Access audio from a file, asset, or capture device, such as a microphone, by using
>   `AssetInputSequenceProvider` or `CaptureInputSequenceProvider`."*
> - *"Use `AnalyzerInputConverter` to convert `AVAudioBuffer` data into formats that `AnalyzerInput`
>   supports."*

That is it. Three new classes, all on the **input** side. The analyzer, the modules, the results,
the assets, the presets and the custom-vocabulary DSL are all unchanged from iOS 26 (or iOS 17, in
the custom-vocabulary case). The 2026 story for Speech is: **you no longer hand-write the audio
plumbing.** That is a smaller change than it sounds and a bigger one than it looks — the audio
plumbing was where most of the bugs were.

---

## 2. The shape of the pipeline

### 2.1 One analyzer, N modules, N result streams

`SpeechAnalyzer` is an **actor**, not a class you subclass and not an object with a delegate.

```swift
final actor SpeechAnalyzer          // iOS 26.0+, iPadOS 26.0+, Mac Catalyst 26.0+,
                                    // macOS 26.0+, tvOS 26.0+, visionOS 26.0+
                                    // Conforms: Actor, Sendable, SendableMetatype
```
✅ VERIFIED — `/documentation/speech/speechanalyzer`.

Apple's own division of labour, verbatim from that page:

> *The `SpeechAnalyzer` class is responsible for: Holding associated modules; Accepting audio speech
> input; Controlling the overall analysis.*
>
> *Each module is responsible for: Providing guidance on acceptable input; Providing its analysis or
> transcription output.*
>
> *Analysis is asynchronous. Input, output, and session control are decoupled… where an Objective-C
> API might use a delegate to provide results to you, the Swift API's modules provide their results
> via an `AsyncSequence`.*

And the constraint that shapes every design decision downstream:

> *The analyzer can only analyze one input sequence at a time.*

So the mental model is a **fan-out**, not a chain:

```
                       ┌──────────────────────────┐
                       │  AsyncSequence           │
   microphone ────────►│  <AnalyzerInput>         │
   or audio file       │  (time-coded PCM)        │
                       └────────────┬─────────────┘
                                    │  analyzeSequence(_:)
                                    ▼
                       ┌──────────────────────────┐
                       │      SpeechAnalyzer      │  actor
                       │   (one sequence at a     │
                       │    time; holds modules)  │
                       └──┬───────────────────┬───┘
                          │                   │
             ┌────────────▼──────┐   ┌────────▼───────────┐
             │ DictationTranscri │   │  SpeechDetector    │
             │ ber  (a module)   │   │  (a module)        │
             └────────┬──────────┘   └────────┬───────────┘
                      │ .results               │ .results
                      ▼                        ▼
          AsyncSequence<Result>      AsyncSequence<Result>
          (AttributedString +        (VAD *errors* only —
           time range + isFinal)      see §12)
```

Every module conforms to `SpeechModule`:

```swift
protocol SpeechModule : AnyObject, Sendable          // iOS 26.0+
    var availableCompatibleAudioFormats { get }      // formats this module can analyze,
                                                     // given its configuration
    var results: Self.Results { get }                // an AsyncSequence
    associatedtype Result
    associatedtype Results

protocol LocaleDependentSpeechModule : SpeechModule  // modules with per-locale assets

protocol SpeechModuleResult                          // iOS 26.0+
    var range { get }                    // "The audio input range that this result applies to."
    var isFinal: Bool { get }            // "Whether this result is final at the time it is produced."
    var resultsFinalizationTime { get }  // "The audio input time up to which results from this
                                         //  module have been finalized (after this result).
                                         //  The module's results are final up to but not
                                         //  including this time."
```
✅ VERIFIED — `/documentation/speech/speechmodule`, `/localedependentspeechmodule`,
`/speechmoduleresult`. Conforming modules, per Apple's page: `DictationTranscriber`,
`SpeechDetector`, `SpeechTranscriber`.

🟡 **RECONSTRUCTED — the types of `range` and `resultsFinalizationTime`.** Apple's page gives the
descriptions but not the declarations. Every other time value in this API is a `CMTime`, and
`analyzeSequence(_:)` returns `CMTime?`, so `range` is almost certainly `CMTimeRange` and
`resultsFinalizationTime` a `CMTime`. Code in this guide never annotates them; it lets inference
do the work, which is both idiomatic and immune to being wrong.

### 2.2 Apple's eight-step canonical flow

This is worth internalising because the ordering is load-bearing — three of the steps break
silently if you reorder them (§5.3).

> ✅ **VERIFIED** — `/documentation/speech/speechanalyzer`, verbatim:
>
> 1. *Create and configure the necessary modules.*
> 2. *Ensure the relevant assets are installed or already present. See `AssetInventory`.*
> 3. *Create an input sequence you can use to provide the spoken audio. See helper classes
>    `AssetInputSequenceProvider` and `CaptureInputSequenceProvider`.*
> 4. *Create and configure the analyzer with the modules and input sequence.*
> 5. *Supply audio. See helper class `AnalyzerInputConverter`.*
> 6. *Start analysis.*
> 7. *Act on results.*
> 8. *Finish analysis when desired.*

Note where the new 2026 classes appear: **steps 3 and 5**. Steps 1, 2, 4, 6, 7 and 8 are exactly
what they were in iOS 26.

Apple ships a complete canonical example on that page. It is the closest thing to a "hello world"
this API has, and it is worth reading before the more realistic listings later in this guide:

```swift
import Speech

// Step 1: Modules
guard let locale = SpeechTranscriber.supportedLocale(equivalentTo: Locale.current) else {
    /* Note unsupported language */
}
let transcriber = SpeechTranscriber(locale: locale, preset: .transcription)

// Step 2: Assets
if let installationRequest = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
    try await installationRequest.downloadAndInstall()
}

// Step 3: Input sequence
let (inputSequence, inputBuilder) = AsyncStream.makeStream(of: AnalyzerInput.self)

// Step 4: Analyzer
let audioFormat = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [transcriber])
let analyzer = SpeechAnalyzer(modules: [transcriber])

// Step 5: Supply audio
let converter = AnalyzerInputConverter(analyzerFormat: audioFormat)
Task {
    while /* audio remains */ {
        let buffer = /* Get some audio */
        let inputs = try converter.convert(buffer, at: nil)
        for input in inputs {
            inputBuilder.yield(input)
        }
    }
    let inputs = try converter.flush()
    for input in inputs {
        inputBuilder.yield(input)
    }
    inputBuilder.finish()
}

// Step 7: Act on results
Task {
    do {
        for try await result in transcriber.results {
            let bestTranscription = result.text // an AttributedString
            let plainTextBestTranscription = String(bestTranscription.characters) // a String
            print(plainTextBestTranscription)
        }
    } catch {
        /* Handle error */
    }
}

// Step 6: Perform analysis
let lastSampleTime = try await analyzer.analyzeSequence(inputSequence)

// Step 8: Finish analysis
if let lastSampleTime {
    try await analyzer.finalizeAndFinish(through: lastSampleTime)
} else {
    try analyzer.cancelAndFinishNow()
}
```
✅ VERIFIED — reproduced verbatim from `/documentation/speech/speechanalyzer`, including the
out-of-order step comments (Apple numbers step 7 above step 6 because the results task must be
running before analysis starts).

Three things to notice in that listing, because they are easy to skim past:

1. **`converter.convert(_:at:)` returns an *array*.** So does `flush()`. Both are `throws` and
   both are **synchronous** — no `await`. If you write `let input = try converter.convert(...)`
   and then `yield(input)`, you have a type error, not a subtle bug, so this one at least fails
   loudly.
2. **`audioFormat` is an `AVAudioFormat?` and Apple passes it into
   `AnalyzerInputConverter(analyzerFormat:)` without unwrapping it.** Either the initializer takes
   an optional or the snippet is loose. 🔴 See §15, gap G3.
3. **The results loop lives in its own `Task`, started before analysis.** That structure is not
   decoration. §9 is entirely about what happens when you get the lifetime of that task wrong.

### 2.3 What "finished" means

The analysis session is a state machine with one transition you care about. Apple documents the
finished state precisely, and the third bullet is the one that saves you:

> ✅ **VERIFIED** — `/documentation/speech/speechanalyzer`, verbatim:
>
> *When the analysis session transitions to the finished state:*
> - *The analyzer won't consume additional input from the input sequence (but note that **it
>   doesn't drain or terminate the sequence**)*
> - *Most methods won't do anything; in particular, the analyzer won't accept different input
>   sequences or modules*
> - *Module result streams terminate and modules won't publish additional results, though the app
>   can continue to iterate over already-published results*

And the corollary, which is the single most common way to hang a first implementation:

> ✅ **VERIFIED**, same page, verbatim:
>
> *While you can terminate the input sequence you created with a method such as
> `AsyncStream.Continuation.finish()`, **terminating the input sequence does not generally finish
> the analysis session**, and you can continue the session with a different input sequence. (See
> `finalizeAndFinishThroughEndOfInput()` for an exception.)*

> ⚠️ **SILENT FAILURE — the hang.** Call `inputBuilder.finish()` and stop there, and *nothing
> throws*. `analyzeSequence(_:)` returns. Your app looks like it stopped cleanly. But the module
> result streams **never terminate**, so a `for try await result in transcriber.results` loop
> waits forever, your task group never completes, and whatever `await`s that group hangs — often a
> "stop recording" button handler, which is exactly the moment the user is watching. There is no
> error, no log line, no timeout. The fix is to call one of the analyzer's `finish` methods
> (§7.3), or to use `finalizeAndFinishThroughEndOfInput()`, which is documented as *the* exception
> that treats end-of-input as end-of-session.

Error propagation is equally clean and equally worth knowing:

> ✅ **VERIFIED**, same page, verbatim: *"When the analyzer or its modules' result streams throw an
> error, **the analysis session becomes finished** as described above, and the same error (or a
> `CancellationError`) is thrown from all waiting methods and result streams."*

So an error anywhere ends everything, everywhere, with the same error. You do not need per-module
error recovery; you need one `catch` around the whole session.

### 2.4 The complete `SpeechAnalyzer` API surface

For reference. Every name here is ✅ VERIFIED from `/documentation/speech/speechanalyzer`;
declarations are given where Apple published one, and omitted where it did not.

```swift
// ── Creating ───────────────────────────────────────────────────────────────
init(modules:options:)
init(inputSequence:modules:options:analysisContext:volatileRangeChangedHandler:)
init(inputAudioFile:modules:options:analysisContext:finishAfterFile:volatileRangeChangedHandler:)

// ── Modules ────────────────────────────────────────────────────────────────
func setModules(_:) async throws
var modules

// ── Performing analysis (structured concurrency) ───────────────────────────
final func analyzeSequence<InputSequence>(_ inputSequence: InputSequence) async throws -> CMTime?
    where InputSequence : Sendable,
          InputSequence : AsyncSequence,
          InputSequence.Element == AnalyzerInput
func analyzeSequence(from:) async throws -> CMTime?

// ── Autonomous analysis (fire and forget) ──────────────────────────────────
func start(inputSequence:)
func start(inputAudioFile:finishAfterFile:)

// ── Finalizing / cancelling mid-session ────────────────────────────────────
func cancelAnalysis(before:)   // "Stops analyzing audio predating the given time."
func finalize(through:)        // "Finalizes the modules' analyses."

// ── Finishing the session ──────────────────────────────────────────────────
func cancelAndFinishNow()
func finalizeAndFinishThroughEndOfInput()
func finalizeAndFinish(through:)
func finish(after:)

// ── Formats ────────────────────────────────────────────────────────────────
static func bestAvailableAudioFormat(compatibleWith modules: [any SpeechModule]) async -> AVAudioFormat?
static func bestAvailableAudioFormat(compatibleWith:considering:) async -> AVAudioFormat?

// ── Responsiveness ─────────────────────────────────────────────────────────
func prepareToAnalyze(in:)
func prepareToAnalyze(in:withProgressReadyHandler:)

// ── Monitoring ─────────────────────────────────────────────────────────────
func setVolatileRangeChangedHandler(_:)
var volatileRange              // "The range of results that can change."

// ── Context ────────────────────────────────────────────────────────────────
func setContext(_:)
var context
```

Two API-design notes that pay off later:

- **`analyzeSequence` vs `start`.** `analyzeSequence(_:)` is the structured-concurrency form: you
  `await` it, it returns when the sequence ends or the task is cancelled, and its return value is
  the timestamp you need for `finalizeAndFinish(through:)`. `start(inputSequence:)` is the
  fire-and-forget form the iOS 26 sample used. **Prefer `analyzeSequence`** — it is what Apple's
  2026 article uses, and it is what makes the cancellation story in §9 tractable.
- **`volatileRange` and `setVolatileRangeChangedHandler(_:)`** exist so you can know, without
  parsing results, which slice of the audio timeline is still subject to revision. If you are
  building a two-transcript UI (§8.2) this is the API that tells you where the boundary is.

---

## 3. Choosing a transcriber

There are two transcriber modules and they are not interchangeable. Picking the wrong one is not a
performance mistake; on some platforms it is a "does not exist" mistake.

### 3.1 The platform matrix

| Symbol | iOS | iPadOS | Mac Catalyst | macOS | tvOS | visionOS | watchOS |
|---|---|---|---|---|---|---|---|
| `SpeechAnalyzer` | 26.0 | 26.0 | 26.0 | 26.0 | **26.0** | 26.0 | ❌ |
| `SpeechTranscriber` | 26.0 | 26.0 | 26.0 | 26.0 | **26.0** | 26.0 | ❌ |
| **`DictationTranscriber`** | 26.0 | 26.0 | 26.0 | 26.0 | ❌ **no tvOS** | 26.0 | ❌ |
| `SpeechDetector` | 26.0 | 26.0 | 26.0 | 26.0 | 26.0 | 26.0 | ❌ |
| `AnalyzerInput`, `AssetInventory` | 26.0 | 26.0 | 26.0 | 26.0 | 26.0 | 26.0 | ❌ |
| **`AnalyzerInputConverter`** | **27.0** | 27.0 | 27.0 | 27.0 | 27.0 | 27.0 | ❌ |
| **`AssetInputSequenceProvider`** | **27.0** | 27.0 | 27.0 | 27.0 | 27.0 | 27.0 | ❌ |
| **`CaptureInputSequenceProvider`** | **27.0** | 27.0 | 27.0 | 27.0 | 27.0 | 27.0 | ❌ |
| `SFCustomLanguageModelData` | 17.0 | 17.0 | 17.0 | **14.0** | ? | **1.1** | ❌ |
| `SFSpeechLanguageModel` | 17.0 | 17.0 | 17.0 | **14.0** | ❌ **no tvOS** | 1.1 | ❌ |

✅ VERIFIED — availability lines read from each symbol's page during the 2026-07-27 documentation
harvest. All the 27.0 rows carry the `Beta` marker.

Two entries deserve emphasis because they are asymmetric in ways that look like typos and are not:

- **`DictationTranscriber` has no tvOS; `SpeechTranscriber` does.** If you are writing for Apple TV,
  `SpeechTranscriber` is your only transcriber, which also means **no content hints and no custom
  language models on tvOS** (§4.4, §11).
- **Neither transcriber lists watchOS at all.** The whole Speech modern stack is absent from
  watchOS 27 — which is notable because Foundation Models *did* gain watchOS 27 this year. Speech
  did not follow. Do not plan a watch dictation feature on this API.

### 3.2 What the two modules actually are

```swift
final class SpeechTranscriber              // iOS 26.0+ … tvOS 26.0+, visionOS 26.0+
                                           // Conforms: LocaleDependentSpeechModule, SpeechModule, Sendable
init(locale:preset:)
init(locale:transcriptionOptions:reportingOptions:attributeOptions:)

static var isAvailable: Bool               // "whether this module is available given the device's
                                           //  hardware and capabilities"
static var installedLocales
static var supportedLocales                // "including locales that may not be installed but
                                           //  are downloadable"
static func supportedLocale(equivalentTo:) -> Locale?
var results                                // AsyncSequence of SpeechTranscriber.Result
```
✅ VERIFIED — `/documentation/speech/speechtranscriber`.

```swift
final class DictationTranscriber           // iOS 26.0+ … visionOS 26.0+ — NO tvOS
init(locale:preset:)
init(locale:contentHints:transcriptionOptions:reportingOptions:attributeOptions:)
static var installedLocales
static var supportedLocales
static func supportedLocale(equivalentTo:)
var results
```
✅ VERIFIED — `/documentation/speech/dictationtranscriber`.

The difference is not "one is better". It is **which models they run**:

> ✅ **VERIFIED** — `/documentation/speech/dictationtranscriber`, verbatim:
>
> *This transcriber uses **the same speech-to-text machine learning models as system dictation
> features** do, or as `SFSpeechRecognizer` does when it is configured for on-device operation.
> **This transcriber does not support languages or locales that `SFSpeechRecognizer` only supports
> via network access.***

`SpeechTranscriber`, by contrast, is the new long-form engine — the one WWDC25 introduced for
"advanced speech-to-text". It is the one with `alternativeTranscriptions`. But Apple also tells you
plainly that it will not exist everywhere:

> ✅ **VERIFIED** — `/documentation/speech/speechtranscriber`, verbatim:
>
> *Use the `isAvailable` or `supportedLocales` properties to see if the current device supports the
> speech-to-text models used by `SpeechTranscriber`. **If it does not, consider disabling the
> feature or using `DictationTranscriber` instead.***

That sentence is your fallback policy, written by Apple. Encode it:

```swift
import Speech

/// Picks the best available transcriber module for a locale, following Apple's documented
/// fallback rule: prefer `SpeechTranscriber`, fall back to `DictationTranscriber`.
///
/// Returns `nil` when neither engine supports the locale at all.
///
/// 🟡 The `any SpeechModule` erasure is ours; Apple's docs do not show a helper of this shape.
/// Everything it calls is ✅ VERIFIED.
func makeTranscriber(preferring locale: Locale) async -> (any SpeechModule)? {
    if SpeechTranscriber.isAvailable,
       let matched = await SpeechTranscriber.supportedLocale(equivalentTo: locale) {
        return SpeechTranscriber(locale: matched, preset: .progressiveTranscription)
    }

    if let matched = await DictationTranscriber.supportedLocale(equivalentTo: locale) {
        return DictationTranscriber(locale: matched, preset: .progressiveLongDictation)
    }

    return nil
}
```

> 🟡 **RECONSTRUCTED — `isAvailable` and `supportedLocale(equivalentTo:)` isolation.** Apple's page
> lists `static var isAvailable: Bool` and `static func supportedLocale(equivalentTo:) -> Locale?`
> but does not publish whether they are actor-isolated or `async`. The iOS 26 sample awaits the
> *collection* properties (`await SpeechTranscriber.supportedLocales`), which implies at least some
> of this surface is isolated. The `await`s above are written defensively; if a member turns out to
> be synchronous, the compiler tells you and you delete one keyword. That is the safe direction to
> be wrong in.

### 3.3 The locale-matching rule you must not shortcut

`supportedLocale(equivalentTo:)` exists because `Locale` equality is not the right test. Apple's
own iOS 26 sample — which we *can* read, and which is the strongest evidence available for this
particular point — compares by BCP-47 identifier, deliberately:

```swift
    func supported(locale: Locale) async -> Bool {
        let supported = await SpeechTranscriber.supportedLocales
        return supported.map { $0.identifier(.bcp47) }.contains(locale.identifier(.bcp47))
    }

    func installed(locale: Locale) async -> Bool {
        let installed = await Set(SpeechTranscriber.installedLocales)
        return installed.map { $0.identifier(.bcp47) }.contains(locale.identifier(.bcp47))
    }
```
✅ VERIFIED — `SwiftTranscriptionSampleApp/Recording and Transcription/Transcription.swift:118-127`
(the WWDC25 sample; this code is iOS 26 but the locale-comparison concern has not changed).

`Locale.current` on a real device carries calendar, measurement-system and hour-cycle preferences
that make direct `==` against a framework-supplied `Locale` fail for reasons that have nothing to
do with language. **Always** go through `supportedLocale(equivalentTo:)` or compare
`.identifier(.bcp47)`. A locale mismatch does not throw — it returns `nil` from the matcher or
`false` from the containment check, and if you wrote `if supported.contains(locale)` you will
conclude the user's language is unsupported when it is fully supported.

### 3.4 Decision table

| If you need… | Use | Because |
|---|---|---|
| Long-form transcription, alternatives, best accuracy | `SpeechTranscriber` | `alternativeTranscriptions` reporting option; the newer engine |
| tvOS | `SpeechTranscriber` | `DictationTranscriber` is not available there |
| **Custom vocabulary / a custom language model** | **`DictationTranscriber`** | `ContentHint.customizedLanguage(modelConfiguration:)` exists only here (§4.4) |
| Far-field audio, atypical speech, or a length hint | `DictationTranscriber` | `.farField`, `.atypicalSpeech`, `.shortForm` content hints |
| Parity with system dictation behaviour | `DictationTranscriber` | Same models as system dictation |
| Emoji or punctuation dictation commands | `DictationTranscriber` | `.punctuation` and `.emoji` transcription options |
| Maximum device coverage with one code path | `DictationTranscriber` with a `SpeechTranscriber` upgrade | `isAvailable` is a `SpeechTranscriber`-only concept |

> ⚠️ **`SpeechTranscriber` has no `ContentHint` at all.** This is the constraint that decides most
> real projects. If your app has domain jargon — medical terms, chess openings, SKU codes, player
> names — the entire custom-language-model path in §11 binds *only* to `DictationTranscriber`. You
> cannot have alternatives *and* custom vocabulary from a single module.
> ✅ VERIFIED by omission: `/documentation/speech/speechtranscriber` lists
> `init(locale:transcriptionOptions:reportingOptions:attributeOptions:)` with **no** `contentHints:`
> parameter, and there is no `SpeechTranscriber.ContentHint` type in the framework index.

---

## 4. Presets, options, and content hints

### 4.1 What a preset is

A preset is a plain value type bundling the three (or four) option sets a transcriber initializer
takes. It is not magic and it is not privileged — Apple says so:

```swift
struct SpeechTranscriber.Preset          // Equatable, Hashable, Sendable
init(transcriptionOptions:reportingOptions:attributeOptions:)
var attributeOptions, reportingOptions, transcriptionOptions

struct DictationTranscriber.Preset       // note the extra member
init(contentHints:transcriptionOptions:reportingOptions:attributeOptions:)
var attributeOptions, contentHints, reportingOptions, transcriptionOptions
```
✅ VERIFIED — `/documentation/speech/speechtranscriber/preset`,
`/documentation/speech/dictationtranscriber/preset`. Apple adds: *"You can also create your own
presets by extending this type."*

That matters because the two-argument `init(locale:preset:)` is a convenience. The moment you need
to add one option, you stop using it and start using the designated initializer, decomposing the
preset yourself. §4.3 shows the pattern; §8.3 shows why you will almost certainly need it.

### 4.2 The two preset matrices

These tables are the highest-value reference in this section. Both are transcribed verbatim from
Apple's preset pages.

**`DictationTranscriber.Preset`** — ✅ VERIFIED, `/documentation/speech/dictationtranscriber/preset`:

| Preset | `shortForm` hint | `.volatileResults` | `.frequentFinalization` | `.audioTimeRange` | `.punctuation` |
|---|---|---|---|---|---|
| `phrase` | **Yes** | No | No | No | No |
| `shortDictation` | **Yes** | No | No | No | **Yes** |
| `progressiveShortDictation` | **Yes** | **Yes** | **Yes** | No | **Yes** |
| `longDictation` | No | No | No | No | **Yes** |
| **`progressiveLongDictation`** | No | **Yes** | No | **No** | **Yes** |
| `timeIndexedLongDictation` | No | No | No | **Yes** | **Yes** |

Apple's one-line descriptions, verbatim:

- `phrase` — *"Configuration for a short phrase without punctuation."*
- `shortDictation` — *"Configuration for about a minute of audio."*
- `progressiveShortDictation` — *"Configuration for immediate transcription of about a minute of
  live audio."*
- `longDictation` — *"Configuration for more than a minute of audio."*
- `progressiveLongDictation` — *"Configuration for immediate transcription of lengthy audio."*
- `timeIndexedLongDictation` — *"Configure for lengthy audio, cross-referencing words to
  time-codes."*

**`SpeechTranscriber.Preset`** — ✅ VERIFIED, `/documentation/speech/speechtranscriber/preset`:

| Preset | `.volatileResults` | `.fastResults` | `.alternativeTranscriptions` | `.audioTimeRange` |
|---|---|---|---|---|
| `transcription` | No | No | No | No |
| `transcriptionWithAlternatives` | No | No | **Yes** | No |
| `timeIndexedTranscriptionWithAlternatives` | No | No | **Yes** | **Yes** |
| `progressiveTranscription` | **Yes** | **Yes** | No | No |
| `timeIndexedProgressiveTranscription` | **Yes** | **Yes** | No | **Yes** |

Descriptions, verbatim:

- `transcription` — *"Configuration for basic, accurate transcription."*
- `transcriptionWithAlternatives` — *"Configuration for transcription with editing suggestions."*
- `timeIndexedTranscriptionWithAlternatives` — *"Configuration for transcription with editing
  suggestions, cross-referenced to source audio."*
- `progressiveTranscription` — *"Configuration for immediate transcription of live audio."*
- `timeIndexedProgressiveTranscription` — *"Configuration for immediate transcription of live audio,
  cross-referenced to stream time-codes."*

**Read the `.audioTimeRange` columns.** Only three presets across both transcribers turn it on:
`timeIndexedLongDictation`, `timeIndexedTranscriptionWithAlternatives` and
`timeIndexedProgressiveTranscription`. Every preset with "timeIndexed" in the name has it; no
other preset does. Hold that thought until §8.3, where it turns into the nastiest bug in this
guide.

### 4.3 The option enums, and how to modify a preset

```swift
enum SpeechTranscriber.TranscriptionOption      // CaseIterable, Equatable, Hashable, Sendable
case etiquetteReplacements   // "Replaces certain words and phrases with a redacted form."

enum SpeechTranscriber.ReportingOption
case alternativeTranscriptions // "Includes alternative transcriptions in addition to the most
                               //  likely transcription."
case fastResults               // "Biases the transcriber towards responsiveness, yielding faster
                               //  but also less accurate results."
case volatileResults           // "Provides tentative results for an audio range in addition to
                               //  the finalized result."

enum SpeechTranscriber.ResultAttributeOption
case audioTimeRange            // "Includes time-code attributes in a transcription's attributed
                               //  string."
case transcriptionConfidence   // "Includes confidence attributes in a transcription's attributed
                               //  string."
```
✅ VERIFIED — `/documentation/speech/speechtranscriber/transcriptionoption`, `/reportingoption`,
`/resultattributeoption`.

> **Note what is missing from the preset matrix: `transcriptionConfidence`.** No preset enables it.
> If you want per-run confidence attributes you *must* use the designated initializer. This is a
> good example of why treating presets as the whole API is limiting.

Apple's own example of modifying a preset (reproduced with its bug intact, because you will hit it):

```swift
let preset = SpeechTranscriber.Preset.timeIndexedTranscriptionWithAlternatives
let transcriber = SpeechTranscriber(
    locale: Locale.current,
    transcriptionOptions: preset.transcriptionOptions.union([.etiquetteReplacements])
    reportingOptions: preset.reportingOptions.subtracting([.alternativeTranscriptions])
    attributeOptions: preset.attributeOptions
)
```
✅ VERIFIED as reproduced — `/documentation/speech/speechtranscriber/preset`.
⚠️ **Apple's snippet is missing the commas between arguments and does not compile as printed.** The
`DictationTranscriber.Preset` page has the identical defect in its own example. This is worth
saying out loud because a reader who copies it and gets a parse error will reasonably assume they
misunderstood the API rather than that Apple's docs have a typo. Add the commas.

The important structural fact those snippets teach: **the option collections are `Set`-like** —
`.union(_:)` and `.subtracting(_:)` work on them. So the idiom for "the preset, plus one thing" is:

```swift
// The compiling version of Apple's example.
let preset = SpeechTranscriber.Preset.timeIndexedTranscriptionWithAlternatives
let transcriber = SpeechTranscriber(
    locale: matchedLocale,
    transcriptionOptions: preset.transcriptionOptions.union([.etiquetteReplacements]),
    reportingOptions: preset.reportingOptions.subtracting([.alternativeTranscriptions]),
    attributeOptions: preset.attributeOptions.union([.transcriptionConfidence])
)
```
🟡 RECONSTRUCTED only in the sense that the commas are ours and `.transcriptionConfidence` was
added to demonstrate the pattern. Every identifier is ✅ VERIFIED.

> 🔴 **GAP — the full case lists for `DictationTranscriber`'s option enums.** We have confirmed
> `DictationTranscriber.TranscriptionOption.punctuation` and `.emoji`,
> `DictationTranscriber.ReportingOption.volatileResults` and `.frequentFinalization`, and
> `DictationTranscriber.ResultAttributeOption.audioTimeRange` — all inferred from the preset matrix
> and from Apple's example snippet. The individual enum pages were **not fetched**, so there may be
> more cases (a `transcriptionConfidence` analogue, in particular, would be unsurprising).
> **Resolving this** needs `/documentation/speech/dictationtranscriber/transcriptionoption`,
> `/reportingoption` and `/resultattributeoption`, or an SDK interface dump.
> **Safe default:** build option sets by starting from a preset and unioning only the cases listed
> above. Do not write an exhaustive `switch` over any of these enums — they are documented as
> `CaseIterable` but nothing says they are frozen.

### 4.4 Content hints — `DictationTranscriber` only

```swift
struct DictationTranscriber.ContentHint          // Equatable, Hashable, Sendable
static var shortForm       // "A processing hint indicating that the audio is only expected to be
                           //  a minute or so long."
static var farField        // "A processing hint indicating that the audio should be processed as
                           //  if it were from a speaker far from the microphone."
static var atypicalSpeech  // "A processing hint indicating that the audio is from a speaker with
                           //  a heavy accent, lisp, or other confounding factor."
static func customizedLanguage(modelConfiguration:)
                           // "A hint specifying a custom language model applicable to the expected
                           //  spoken audio content."
```
✅ VERIFIED — `/documentation/speech/dictationtranscriber/contenthint`.

Apple's caveat on all of them, verbatim: *"These hints optimize transcription, but **do not preclude
spoken audio with different characteristics**."* In other words a hint is a bias, not a filter.
`farField` does not stop close-mic audio from transcribing; `shortForm` does not truncate at 60
seconds. They tune the algorithm's priors.

`atypicalSpeech` deserves a specific mention because it is the accessibility lever in this API and
it is easy to miss. If your app serves users with speech differences, this is a one-line change
with real impact and no downside for other users beyond the hint's own bias.

Apple documents **three** accuracy levers for `DictationTranscriber`, and they are independent —
you can use all three at once:

> ✅ **VERIFIED** — `/documentation/speech/dictationtranscriber`, verbatim:
>
> - *To **bias recognition towards certain words**, create an `AnalysisContext` object and add
>   those words to its `contextualStrings` property. Create a `SpeechAnalyzer` instance with that
>   context object or set the analyzer's `context` property.*
> - *To **supply custom vocabulary**, create an `SFSpeechLanguageModel` object and configure the
>   transcriber with a corresponding `customizedLanguage(modelConfiguration:)` option.*
> - *To **adjust the transcriber's algorithm**, configure the transcriber with relevant
>   `DictationTranscriber.ContentHint` parameter. For example, you may use `farField` hint to
>   improve accuracy of distant speech.*

Those are three different mechanisms at three different costs, and choosing between them is a real
engineering decision:

| Lever | Cost | When it fits | Where it lives |
|---|---|---|---|
| `AnalysisContext.contextualStrings` | Free, runtime, changeable per-session | A handful of names you know *right now* — the contacts on screen, today's calendar entries | `analyzer.context` / `setContext(_:)`, iOS 26.0+ |
| `ContentHint.customizedLanguage(modelConfiguration:)` | An **offline build step** producing a binary blob, plus a `prepareCustomLanguageModel` call at launch | A fixed domain vocabulary — chess openings, drug names, aircraft types | §11, iOS 17.0+ types |
| Other `ContentHint`s | Free, one line | You know something structural about the audio | §4.4 |

The middle row is the heavy one and the only one that needs tooling. §11 covers it end to end.

Here is the pattern Apple's 2026 article uses to attach a custom language model — note that it
**unions** the hint into the preset's hints rather than replacing them, so the preset's own tuning
survives:

```swift
let preset = DictationTranscriber.Preset.progressiveLongDictation

// Set customized language model if one is given.
let contentHints = if let lmConfiguration {
    preset.contentHints.union([.customizedLanguage(modelConfiguration: lmConfiguration)])
} else {
    preset.contentHints
}

return DictationTranscriber(
    locale: locale,
    contentHints: contentHints,
    transcriptionOptions: preset.transcriptionOptions,
    reportingOptions: preset.reportingOptions,
    attributeOptions: preset.attributeOptions
)
```
✅ VERIFIED — quoted verbatim from *"Recognizing speech in live audio"*, §"Configure the speech
analyzer". `lmConfiguration` is an optional `SFSpeechLanguageModel.Configuration`.

Note the `if`-expression assigned straight to a `let` — that is Swift 5.9+ style and it is Apple's,
not ours. Note also that the whole function is written so a `nil` configuration degrades cleanly to
the plain preset. That is the right shape: a custom language model is an enhancement, and an app
whose transcription breaks because a `.bin` failed to prepare is a worse app than one that
transcribes "Winawer" as "we know where".

> ⚠️ **This code is where the `progressiveLongDictation` trap is born.** It passes
> `attributeOptions: preset.attributeOptions` unchanged — and per the matrix in §4.2,
> `progressiveLongDictation` does **not** include `.audioTimeRange`. Hold that. §8.3.

---

## 5. Assets: `AssetInventory` and the reservation quota

### 5.1 Why this class exists

`AssetInventory` is the part of the API that developers most often skip, because in a simulator or
on a personal device that has already dictated something, everything works without it. It exists
because **the speech models are not in your app and they are not in the OS image**.

> ✅ **VERIFIED** — `/documentation/speech/assetinventory`, verbatim:
>
> *These assets are **machine-learning models downloaded from Apple's servers and managed by the
> system**. Once you download, install, or use an asset, the system **retains and updates it
> automatically, and shares it with other apps**. The system makes a certain number of
> **locale-specific asset reservations** available to your app to limit storage space and network
> usage.*
>
> ***Your app does not work with assets directly.** Instead, your app configures module objects.
> The system uses the modules' configuration to determine what assets are relevant.*
>
> *Once assets are downloaded, they persist between app launches and are shared between apps.
> **The system may unsubscribe your app from assets that haven't been used in a while.***
>
> *When your app no longer needs assets for a particular locale, call `release(reservedLocale:)` to
> free up that reservation. **The system will remove the assets at a later time.***

Four consequences that should shape your code:

1. **You never name an asset.** You hand `AssetInventory` a configured module and it works out
   what that module needs. Which means an asset request is only as correct as your module's
   configuration — change the locale or the content hints and you may need a different asset.
2. **Assets are shared across apps.** The first download on a device may be free because Messages
   or Notes already pulled it. This is why "it worked on my phone" is a genuinely misleading signal.
3. **There is a quota.** `maximumReservedLocales` is real and `assetInstallationRequest` throws
   when auto-reservation would exceed it.
4. **The system can unsubscribe you.** An app that transcribes once a quarter can find its assets
   gone. Check status on every launch, not once at first-run.

### 5.2 The API

```swift
final class AssetInventory                 // iOS 26.0+ … tvOS 26.0+, visionOS 26.0+

static func assetInstallationRequest(supporting modules: [any SpeechModule])
    async throws -> AssetInstallationRequest?
static func reserve(locale:) async throws
static func release(reservedLocale:) async
static var reservedLocales
static var maximumReservedLocales: Int
static func status(forModules:) async -> AssetInventory.Status

enum AssetInventory.Status                 // Comparable, Equatable, Hashable
case downloading   // "The system is currently downloading the assets, or waiting for conditions
                   //  to improve and continue downloading later."
case installed     // "The necessary assets have been downloaded and installed on the device, and
                   //  the module is ready for use."
case supported     // "The module can work with its configuration, but the assets will need to be
                   //  downloaded."
case unsupported   // "The module will not work with its configuration."
```
✅ VERIFIED — `/documentation/speech/assetinventory`, `/documentation/speech/assetinventory/status`.

```swift
@objc final class AssetInstallationRequest    // inherits NSObject, conforms ProgressReporting
func downloadAndInstall() async throws
```
✅ VERIFIED — `/documentation/speech/assetinstallationrequest`. Conforming to `ProgressReporting`
means it has a `progress: Progress` you can bind straight into SwiftUI's `ProgressView`.

Apple adds: *"You do not create instances of this type directly. **The system consolidates download
and installation requests; you may obtain several of these instances and call `downloadAndInstall()`
several times without causing redundant downloads**."* That is a licence to be sloppy in a good
way — if two screens both ensure assets on appear, you have not doubled the download.

> 🔴 **GAP — `AssetInventory.Status` is `Comparable` but the ordering is unpublished.** The natural
> reading is `unsupported < supported < downloading < installed`, which would make
> `if await AssetInventory.status(forModules: [m]) >= .supported` a clean guard. We could not
> confirm it. **Resolving this** needs the SDK interface or a one-line experiment on a macOS 27
> machine (`print([Status.installed, .downloading, .supported, .unsupported].sorted())`).
> **Safe default:** `switch` on the four cases explicitly. It is three more lines and it cannot be
> wrong.

### 5.3 The four-step process, and the ordering that matters

> ✅ **VERIFIED** — `/documentation/speech/assetinventory`, verbatim:
>
> 1. *Create analyzer modules in the configurations that you wish to use. **These modules can be
>    discarded when no longer needed; the system installs assets using the modules' configuration,
>    not their object identity.***
> 2. *Assign your app's asset reservations to those locales. The class does this automatically if
>    needed, but you can also call `reserve(locale:)` to do this manually. **This step is only
>    necessary for modules with locale-specific assets**; that is, modules conforming to
>    `LocaleDependentSpeechModule`.*
> 3. *Start downloading the required assets… Call `assetInstallationRequest(supporting:)` to obtain
>    an instance of `AssetInstallationRequest` and call its `downloadAndInstall()` method.*
> 4. *Wait for the download to finish. Note that **the download may finish immediately**; the
>    assets may have already been downloaded if the assets were preinstalled on the system, another
>    app already downloaded them, or a previous module configuration used the same assets.*

Step 1's parenthetical is unusually generous API design and worth exploiting: **you can create a
throwaway module purely to describe an asset requirement**, install the asset, discard it, and
create the real module later. Prefetching at app launch for a locale the user has not yet selected
is a two-line operation.

Now the two return-value contracts that bite:

> ✅ **VERIFIED** — `/documentation/speech/assetinventory/assetinstallationrequest(supporting:)`,
> verbatim:
>
> *If the current status is `.installed`, **returns nil**, indicating that nothing further needs to
> be done.*
>
> *If some of the assets require locales that aren't reserved, **it automatically reserves those
> locales. If that would exceed `maximumReservedLocales`, then it throws an error**.*

> ⚠️ **SILENT FAILURE — force-unwrapping the installation request.** `assetInstallationRequest`
> returning `nil` is the *success* case for an already-provisioned device. Writing
> `try await AssetInventory.assetInstallationRequest(supporting: [t])!.downloadAndInstall()` crashes
> on precisely the devices where everything is fine, and works on the fresh ones you test on. Use
> `if let`. Apple's own code does, in both the iOS 26 sample and the 2026 article.

Here is the 2026 article's version, which is as short as this gets:

```swift
let transcriber = createDictationTranscriber(locale: locale, lmConfiguration: lmConfiguration)
if let request = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
    try await request.downloadAndInstall()
}
```
✅ VERIFIED — verbatim from *"Recognizing speech in live audio"*, §"Prepare to record and transcribe
speech".

And here is the iOS 26 sample's fuller ladder, which adds the two guards the short form skips and
is the version worth shipping:

```swift
    public func ensureModel(transcriber: SpeechTranscriber, locale: Locale) async throws {
        guard await supported(locale: locale) else {
            throw TranscriptionError.localeNotSupported
        }
        if await installed(locale: locale) {
            return
        } else {
            try await downloadIfNeeded(for: transcriber)
        }
    }

    func downloadIfNeeded(for module: SpeechTranscriber) async throws {
        if let downloader = try await AssetInventory.assetInstallationRequest(supporting: [module]) {
            self.downloadProgress = downloader.progress
            try await downloader.downloadAndInstall()
        }
    }

    func releaseLocales() async {
        let reserved = await AssetInventory.reservedLocales
        for locale in reserved {
            await AssetInventory.release(reservedLocale: locale)
        }
    }
```
✅ VERIFIED — `SwiftTranscriptionSampleApp/Recording and Transcription/Transcription.swift:108-142`.
⚠️ This is **iOS 26 sample code** and is typed to `SpeechTranscriber`; the same shape applies to
`DictationTranscriber`, but that substitution is ours, not Apple's.

`self.downloadProgress = downloader.progress` is the line to copy. `Progress` is
`ObservableObject`-adjacent and `ProgressView(_:)` takes one directly, so a real download bar is
about four lines of SwiftUI.

### 5.4 The reservation quota

`maximumReservedLocales` is a hard number the system gives your app. Nothing in the documentation
says what it is, and it may well vary by device.

> 🔴 **GAP — the value of `maximumReservedLocales`.** Not published on any page we fetched, and
> the API is a property rather than a constant precisely because it is presumably dynamic.
> **Resolving this** takes one line on a device: `print(AssetInventory.maximumReservedLocales)`.
> Add it to your diagnostics screen. **Safe default:** never assume you can hold more than **one**
> reserved locale, release aggressively, and treat the throw from `assetInstallationRequest` as a
> normal, recoverable outcome rather than a programming error.

The recovery path when you hit the quota is `release(reservedLocale:)` on a locale you are done
with, then retry. A multi-language app that lets the user switch transcription language should
release the previous locale on switch, not on quit — the system removes the assets "at a later
time" anyway, so releasing early costs nothing if the user switches back quickly.

```swift
/// Switch transcription locale, releasing the previous reservation first so a multi-language
/// app cannot walk into `maximumReservedLocales`.
///
/// 🟡 Assembled by us from ✅ VERIFIED members. Apple ships no equivalent snippet.
func switchLocale(to newLocale: Locale, currentlyReserved: Locale?) async throws {
    if let currentlyReserved, currentlyReserved != newLocale {
        await AssetInventory.release(reservedLocale: currentlyReserved)
    }

    guard let matched = await DictationTranscriber.supportedLocale(equivalentTo: newLocale) else {
        throw TranscriptionSetupError.localeNotSupported(newLocale)
    }

    let probe = DictationTranscriber(locale: matched, preset: .progressiveLongDictation)
    // The probe module exists only to describe an asset requirement; per Apple, modules
    // "can be discarded when no longer needed."
    if let request = try await AssetInventory.assetInstallationRequest(supporting: [probe]) {
        try await request.downloadAndInstall()
    }
}

enum TranscriptionSetupError: Error {
    case localeNotSupported(Locale)
    case couldNotCaptureMicrophone
    case micPermissionDenied
}
```

### 5.5 What breaks if you skip assets entirely

Three distinct failures, and only one of them looks like a failure.

**1. `bestAvailableAudioFormat` returns `nil`.**

> ✅ **VERIFIED** — `/documentation/speech/speechanalyzer/bestavailableaudioformat(compatiblewith:)`,
> verbatim: *"Returns `nil` if the specified modules require you to install additional assets."*

> ⚠️ **SILENT FAILURE — querying the format before installing assets.** This is the ordering bug
> Apple's eight-step flow is designed to prevent (assets are step 2, format is step 4), and it is
> the most common one. `bestAvailableAudioFormat` does not throw and does not log; it hands back
> `nil`. If your code then does `?? someDefaultFormat`, or force-unwraps in a `Task` whose crash you
> do not see, you end up feeding the analyzer audio in a format its modules never agreed to. And
> because — per the next paragraph — **the analyzer does no conversion**, the result is not an
> error but silence: an empty or garbage transcript with a fully green console.

**2. The analyzer will not fix a format mismatch for you.**

> ✅ **VERIFIED**, same page, verbatim: *"In order to keep `CMTime` values **sample-accurate**, the
> analyzer **does not transparently upsample, downsample, or convert audio input**."*

That is a deliberate trade — sample-accurate time codes are what make §8's whole result-merging
model possible — but it means format correctness is entirely your problem. It is also exactly why
`AnalyzerInputConverter` and the two sequence providers were added in 2026: they exist so the
correct format is obtained and applied for you (§6).

**3. `assetInstallationRequest` throws on quota exhaustion**, per §5.3. This one *does* throw, so
it is the friendly failure of the three.

The rule that follows: **assets first, format second, analyzer third, audio fourth.** Write it as a
single `prepare()` function so the ordering cannot drift.

---

## 6. Input: `CaptureInputSequenceProvider` and friends

This is the headline change of 2026 and the only part of the framework that actually moved.

### 6.1 What you used to have to write

In iOS 26 there was exactly one way to get microphone audio into a `SpeechAnalyzer`: build an
`AsyncStream<AnalyzerInput>` by hand, install a tap on an audio engine node, convert every buffer
into the analyzer's format yourself, wrap each converted buffer in an `AnalyzerInput`, and yield it.
Apple's iOS 26 sample does exactly that:

```swift
        self.analyzerFormat = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [transcriber])
        (inputSequence, inputBuilder) = AsyncStream<AnalyzerInput>.makeStream()
```
✅ VERIFIED — `SwiftTranscriptionSampleApp/Recording and Transcription/Transcription.swift:57-58`
(iOS 26 sample). The buffer-conversion and `yield(AnalyzerInput(buffer:))` code sits at
`Transcription.swift:88-97`.

That code is not hard, but it is *fiddly*, and every fiddly bit is a silent failure waiting to
happen: the converter's output format has to match `bestAvailableAudioFormat` exactly; the tap's
buffer size interacts with latency; a dropped `flush()` loses the tail of the recording; and
`AVAudioConverter`'s many-to-many frame mapping means one input buffer does not produce one output
buffer.

### 6.2 What you write now

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, §"Configure the capture session",
> verbatim:
>
> *The speech analyzer processes audio taken from an asynchronous sequence; the app must convert the
> audio to a format that the transcriber module can work with and add it to that sequence. The app
> uses `CaptureInputSequenceProvider` to do that. **This class sets up a capture session, audio
> conversion pipeline, and asynchronous sequence that are compatible with the speech analyzer and
> transcriber module. The provider also configures the session automatically, eliminating the need
> to install audio engine taps to convert and route audio buffers.***

Two lines:

```swift
guard let captureDevice = AVCaptureDevice.default(.microphone, for: .audio, position: .unspecified) else {
    throw TranscriptionError.couldNotCaptureMicrophone
}

let provider = try await CaptureInputSequenceProvider.providerWithSession(from: captureDevice, compatibleWith: modules)
```
✅ VERIFIED — both fragments quoted verbatim from *"Recognizing speech in live audio"*.
`TranscriptionError` is the sample's own error type.

`providerWithSession` is doing four jobs that used to be yours: creating an `AVCaptureSession`,
adding an input for the device, asking the modules what audio format they want and installing a
conversion pipeline that produces it, and exposing the result as an `AsyncSequence<AnalyzerInput>`
with correct time codes.

### 6.3 The complete `CaptureInputSequenceProvider` surface

```swift
final class CaptureInputSequenceProvider        // iOS 27.0+ Beta, iPadOS 27.0+ Beta,
                                                // Mac Catalyst 27.0+ Beta, macOS 27.0+ Beta,
                                                // tvOS 27.0+ Beta, visionOS 27.0+ Beta

static func providerWithSession(from:compatibleWith:priority:)
    // "configures a NEW audio capture session with that device"
static func provider(from:in:compatibleWith:priority:)
    // uses an EXISTING session
init(session:analyzerFormat:priority:)

var analyzerInputs                              // AsyncSequence of AnalyzerInput
var captureSession                              // "The underlying capture session."
var captureAudioDataOutput                      // "An audio data output that routes and converts
                                                //  captured audio buffers to async sequences."
```
✅ VERIFIED — `/documentation/speech/captureinputsequenceprovider`.

The three entry points map onto three levels of "how much of my audio stack do I already own":

| You have | Use | What you give up |
|---|---|---|
| Nothing; you just want the mic | `providerWithSession(from:compatibleWith:)` | Control over the session's other configuration — but you get `captureSession` back and can adjust it |
| An existing `AVCaptureSession` (a camera app, say) | `provider(from:in:compatibleWith:priority:)` | Nothing; this is the composition path |
| A session *and* you already know the analyzer format | `init(session:analyzerFormat:priority:)` | The automatic format negotiation; you must supply the right `AVAudioFormat` |

Apple's own note on mixing with an existing session, verbatim from the article:

> *An app may also configure a capture session independently. **The input sequence provider can
> supply an output destination object that the app can add to its session.***

That "output destination object" is `captureAudioDataOutput`, described on the reference page as
*"An audio data output that routes and converts captured audio buffers to async sequences."* So the
third integration mode is: build your own session, take the provider's
`captureAudioDataOutput`, `addOutput` it, and read `analyzerInputs`.

> 🔴 **GAP — the type of `captureAudioDataOutput`, and whether `priority:` is defaulted.** Apple's
> page gives the member names and descriptions but no declarations. The name strongly suggests an
> `AVCaptureAudioDataOutput` subclass or wrapper, and `priority:` appears as a trailing parameter on
> both static factories while the article calls
> `providerWithSession(from:compatibleWith:)` with only two arguments — which implies it *is*
> defaulted. **Resolving this** needs an SDK interface dump (`swift-ide-test` or Xcode's
> "Jump to Definition" on macOS 27). **Safe default:** call the two-argument form the article uses,
> and if you need the output object, bind it with `let output = provider.captureAudioDataOutput`
> and let inference tell you the type.

### 6.4 Complete microphone capture, end to end

This is a full, copyable file. Every Speech and AVFoundation call in it is ✅ VERIFIED from Apple's
article or reference pages; the class scaffolding, the actor, and the error enum are ours and
marked.

```swift
import Speech
import AVFoundation
import CoreMedia

/// Owns the capture session on a single isolation domain.
///
/// 🟡 Our scaffolding — but it exists for a reason Apple states explicitly:
/// "To avoid concurrency-related compilation errors, the app actually saves the session
/// instance in an actor and manages the session through that actor."
/// (✅ VERIFIED, "Recognizing speech in live audio", §"Configure the capture session".)
actor CaptureSessionBox {
    private var session: AVCaptureSession?

    func adopt(_ session: AVCaptureSession) {
        self.session = session
    }

    func start() {
        session?.startRunning()
    }

    func stop() {
        session?.stopRunning()
    }

    /// Apple: "the only way to fully end a capture session is to release all references to it
    /// and let it deallocate." (✅ VERIFIED, same article, §"Stop the capture session".)
    func release() {
        session?.stopRunning()
        session = nil
    }
}

enum TranscriptionError: Error {
    case couldNotCaptureMicrophone
    case micPermissionDenied
    case localeNotSupported(Locale)
    case noTranscriberAvailable
}

@MainActor
final class LiveTranscription {

    private let sessionBox = CaptureSessionBox()
    private var recordingTask: Task<Void, Error>?

    /// Displayed text. Assembled by us from the module's results — the module does not
    /// accumulate a transcript (§8).
    private(set) var transcript = AttributedString()

    // ── Setup ──────────────────────────────────────────────────────────────

    /// Step 1 + step 2 of Apple's eight-step flow: build the module, then install its assets.
    /// Order is load-bearing (§5.5).
    private func makeTranscriber(
        locale: Locale,
        lmConfiguration: SFSpeechLanguageModel.Configuration?
    ) -> DictationTranscriber {
        // ✅ VERIFIED — this function body is quoted from Apple's article, with
        //    `.audioTimeRange` added to attributeOptions. See §8.3 for why that addition
        //    is not optional if you plan to use rangeOfAudioTimeRangeAttributes.
        let preset = DictationTranscriber.Preset.progressiveLongDictation

        let contentHints = if let lmConfiguration {
            preset.contentHints.union([.customizedLanguage(modelConfiguration: lmConfiguration)])
        } else {
            preset.contentHints
        }

        return DictationTranscriber(
            locale: locale,
            contentHints: contentHints,
            transcriptionOptions: preset.transcriptionOptions,
            reportingOptions: preset.reportingOptions,
            attributeOptions: preset.attributeOptions.union([.audioTimeRange])
        )
    }

    func prepare(
        locale: Locale = .current,
        lmConfiguration: SFSpeechLanguageModel.Configuration? = nil
    ) async throws {
        guard let matched = await DictationTranscriber.supportedLocale(equivalentTo: locale) else {
            throw TranscriptionError.localeNotSupported(locale)
        }

        // Step 2: assets. A throwaway module is fine here — the system installs assets using
        // the module's *configuration*, not its identity.
        let probe = makeTranscriber(locale: matched, lmConfiguration: lmConfiguration)
        if let request = try await AssetInventory.assetInstallationRequest(supporting: [probe]) {
            try await request.downloadAndInstall()
        }

        // Permission. ✅ VERIFIED call, quoted from the article.
        guard await AVCaptureDevice.requestAccess(for: .audio) else {
            throw TranscriptionError.micPermissionDenied
        }
    }

    // ── Recording ──────────────────────────────────────────────────────────

    func startRecording(
        locale: Locale = .current,
        lmConfiguration: SFSpeechLanguageModel.Configuration? = nil
    ) {
        recordingTask = Task { [weak self] in
            guard let self else { return }
            try await self.runSession(locale: locale, lmConfiguration: lmConfiguration)
        }
    }

    /// Apple: "When the user taps the Stop Recording button, the app simply cancels that task."
    /// ✅ VERIFIED, §"Stop the capture session".
    func stopRecording() {
        recordingTask?.cancel()
    }

    private func runSession(
        locale: Locale,
        lmConfiguration: SFSpeechLanguageModel.Configuration?
    ) async throws {
        guard let matched = await DictationTranscriber.supportedLocale(equivalentTo: locale) else {
            throw TranscriptionError.localeNotSupported(locale)
        }

        // Step 1: modules.
        let transcriber = makeTranscriber(locale: matched, lmConfiguration: lmConfiguration)
        let modules: [any SpeechModule] = [transcriber]

        // Step 4: analyzer.
        // ✅ VERIFIED shape — "let analyzer = SpeechAnalyzer(modules: modules)".
        let analyzer = SpeechAnalyzer(modules: modules)

        // Step 3: input sequence, via the 2026 provider.
        guard let captureDevice = AVCaptureDevice.default(.microphone,
                                                          for: .audio,
                                                          position: .unspecified) else {
            throw TranscriptionError.couldNotCaptureMicrophone
        }
        let provider = try await CaptureInputSequenceProvider.providerWithSession(
            from: captureDevice,
            compatibleWith: modules
        )
        await sessionBox.adopt(provider.captureSession)

        // Steps 5–8, as two subtasks with opposite cancellation requirements. See §9.
        try await withThrowingDiscardingTaskGroup { group in
            group.addTask {
                try await self.captureAndAnalyzeAudio(
                    analyzer: analyzer,
                    audioSequence: provider.analyzerInputs
                )
            }

            group.addTask {
                // ⚠️ The shield is not optional. Without it you lose the tail of every
                //    recording, silently. §9.
                try await withTaskCancellationShield {
                    try await self.updateTranscription(transcriber: transcriber)
                }
            }
        }
    }

    private func captureAndAnalyzeAudio(
        analyzer: SpeechAnalyzer,
        audioSequence: some AsyncSequence<AnalyzerInput, any Error> & Sendable
    ) async throws {
        await sessionBox.start()
        defer { Task { await self.sessionBox.release() } }

        // ✅ VERIFIED — both lines quoted from the article, §"Analyze audio and display results".
        let lastAudioTime = try await analyzer.analyzeSequence(audioSequence)
        if let lastAudioTime {
            try await analyzer.finalizeAndFinish(through: lastAudioTime)
        }
    }

    private func updateTranscription(transcriber: DictationTranscriber) async throws {
        // ✅ VERIFIED shape — the article maps the results sequence on the main actor:
        //    "let transcriptsSequence = transcriber.results.map { @MainActor transcriberResult in
        //         return self.updateTranscript(with: transcriberResult) }"
        for try await result in transcriber.results {
            await MainActor.run {
                self.merge(result)
            }
        }
    }

    // merge(_:) is §8.
}
```

> 🔴 **GAP — the `AsyncSequence` element/failure types of `provider.analyzerInputs`.** Apple
> documents `analyzerInputs` as "an asynchronous sequence" of `AnalyzerInput` but publishes no
> declaration, so the typed-throws spelling above
> (`some AsyncSequence<AnalyzerInput, any Error> & Sendable`) is **ours**. What *is* ✅ VERIFIED is
> the constraint on the receiving side: `analyzeSequence(_:)` is declared
> `where InputSequence : Sendable, InputSequence : AsyncSequence, InputSequence.Element == AnalyzerInput`.
> **Safe default:** do not annotate. Write `let audioSequence = provider.analyzerInputs` and pass it
> straight to `analyzeSequence(_:)`; if it satisfies the constraint the call compiles, and if it
> does not you get a clear diagnostic rather than a wrong guess baked into a signature.

> 🔴 **GAP — `withTaskCancellationShield`.** See §9.4. It appears verbatim in Apple's article and
> nowhere else in our corpus. It may be a Swift concurrency library function or a helper defined
> inside the SpokenWord sample. §9.4 gives you a shield you can write yourself either way.

### 6.5 Files and assets: `AssetInputSequenceProvider`

The file-based sibling. Same shape, different source.

```swift
final class AssetInputSequenceProvider          // iOS 27.0+ Beta … visionOS 27.0+ Beta

static func provider(from:compatibleWith:priority:)
    // "reads from the first track of an asset or file"
static func provider(from:track:compatibleWith:priority:)
init(asset:track:analyzerFormat:priority:)

var analyzerInputs                              // AsyncSequence of AnalyzerInput
```
✅ VERIFIED — `/documentation/speech/assetinputsequenceprovider`.

The two static factories differ only in whether you name a track. `provider(from:compatibleWith:)`
reads *the first track*, which is right for a voice memo and wrong for a movie with a music bed on
track 1 and dialogue on track 2.

```swift
import Speech
import AVFoundation

/// Transcribe a whole file, batch-style, with no volatile results and no UI churn.
///
/// 🟡 Assembled by us. Every call is ✅ VERIFIED; the composition is not from Apple.
func transcribeFile(at url: URL, locale: Locale = .current) async throws -> String {
    guard let matched = await SpeechTranscriber.supportedLocale(equivalentTo: locale) else {
        throw TranscriptionError.localeNotSupported(locale)
    }

    // For batch work you want accuracy, not immediacy: no volatile results to merge.
    let transcriber = SpeechTranscriber(locale: matched, preset: .transcription)
    let modules: [any SpeechModule] = [transcriber]

    if let request = try await AssetInventory.assetInstallationRequest(supporting: modules) {
        try await request.downloadAndInstall()
    }

    let asset = AVURLAsset(url: url)
    let provider = try await AssetInputSequenceProvider.provider(
        from: asset,
        compatibleWith: modules
    )

    let analyzer = SpeechAnalyzer(modules: modules)

    var text = AttributedString()

    try await withThrowingDiscardingTaskGroup { group in
        group.addTask {
            let lastAudioTime = try await analyzer.analyzeSequence(provider.analyzerInputs)
            if let lastAudioTime {
                try await analyzer.finalizeAndFinish(through: lastAudioTime)
            }
        }
        group.addTask {
            // With `.transcription` there are no volatile results, so every result is final
            // and append-only. This is the simplest merge strategy there is (§8.4).
            for try await result in transcriber.results {
                text.append(result.text)
            }
        }
    }

    return String(text.characters)
}
```

> 🟡 **RECONSTRUCTED — `AVURLAsset(url:)` as the argument to `provider(from:)`.** Apple's page says
> the factory "reads from the first track of an asset or file" and names the parameter `from:`, but
> does not publish its type. `AVAsset`/`AVURLAsset` is the obvious reading and matches the class
> name. **Safe default:** if `AVURLAsset` does not type-check, try passing the `URL` directly — the
> documentation phrase "an asset **or file**" suggests overloads for both.

Notice how much simpler the file path is than the live one. There is no cancellation shield, no
capture session to release, and no volatile-result merging — because a file has a natural end. That
is exactly Apple's own advice:

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, §"Stop the capture session", verbatim:
>
> *…an app that uses another kind of audio sequence, such as one obtained from an
> `AssetInputSequenceProvider` or one that the app itself creates, **can simply finish the analysis
> session after the audio sequence ends and `analyzeSequence(_:)` returns normally**.*

**If your audio has an end, use it.** The complexity in §9 is the price of a microphone that never
stops on its own.

### 6.6 When you still need `AnalyzerInputConverter`

The two providers cover microphone and file. Everything else — a network stream, a game engine's
audio bus, a Core Audio unit, a `.wav` you are synthesizing — is yours, and `AnalyzerInputConverter`
is the piece that makes "yours" tolerable.

```swift
final class AnalyzerInputConverter              // iOS 27.0+ Beta … visionOS 27.0+ Beta
static func converter(compatibleWith:) -> AnalyzerInputConverter
init(analyzerFormat:configurationHandler:)
func convert(_:at:) throws -> [AnalyzerInput]
func flush() throws -> [AnalyzerInput]
```
✅ VERIFIED — `/documentation/speech/analyzerinputconverter`. The framework changelog describes it
as converting *"`AVAudioBuffer` data into formats that `AnalyzerInput` supports."*

Three things to get right:

1. **`convert(_:at:)` returns an array**, because format conversion is many-to-many at the frame
   level. One input buffer can produce zero, one, or several `AnalyzerInput`s. Yield all of them.
2. **`flush()` exists and matters.** A converter with a non-trivial resampling ratio holds frames
   internally. If you never call `flush()`, the last fraction of a second of every recording is
   dropped inside the converter, before the analyzer ever sees it. No error. This is a second,
   independent way to lose the tail of a recording — distinct from the §9 cancellation bug and
   equally invisible.
3. **`init(analyzerFormat:configurationHandler:)` is used in Apple's canonical example with one
   argument**, so `configurationHandler:` is defaulted.

```swift
import Speech
import AVFoundation

/// Hand-rolled input for an audio source neither provider covers.
///
/// ✅ The convert/flush/yield structure is quoted from Apple's canonical example on
///    /documentation/speech/speechanalyzer. The surrounding function is ours.
func makeInputSequence(
    compatibleWith modules: [any SpeechModule],
    buffers: some AsyncSequence<AVAudioPCMBuffer, Never> & Sendable
) async throws -> AsyncStream<AnalyzerInput> {

    // ⚠️ Assets must already be installed or this returns nil (§5.5).
    guard let analyzerFormat = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: modules) else {
        throw TranscriptionError.noTranscriberAvailable
    }

    let converter = AnalyzerInputConverter(analyzerFormat: analyzerFormat)
    let (stream, continuation) = AsyncStream.makeStream(of: AnalyzerInput.self)

    Task {
        do {
            for await buffer in buffers {
                for input in try converter.convert(buffer, at: nil) {
                    continuation.yield(input)
                }
            }
            // Without this, the tail of the audio dies inside the converter.
            for input in try converter.flush() {
                continuation.yield(input)
            }
        } catch {
            // Terminating the stream does NOT finish the analysis session (§2.3).
        }
        continuation.finish()
    }

    return stream
}
```

> 🔴 **GAP — the `at:` parameter of `convert(_:at:)`.** Apple's canonical example passes `nil`, and
> the surrounding documentation on `AnalyzerInput` explains that a time-code is how you handle
> discontiguous audio: *"When you resume analysis with a later `AVAudioPCMBuffer` buffer, you may
> need to supply the correct time-code to account for skipped audio. To do this, pass the time-code
> of the later buffer as the `bufferStartTime` parameter of the corresponding `AnalyzerInput`
> object."* (✅ VERIFIED.) So `at:` is almost certainly an optional `CMTime` playing the same role.
> **Safe default:** pass `nil` for contiguous audio, which is the case for every live capture. If
> you skip audio deliberately, set the time explicitly and expect to verify the type at the call
> site.

### 6.7 `AnalyzerInput` itself

```swift
struct AnalyzerInput                            // iOS 26.0+, Sendable — "Time-coded audio data."
init(buffer:)
init(buffer:bufferStartTime:)                   // "for audio that may be discontiguous with
                                                //  previous input"
var bufferStartTime                             // "The time-code of this input."
var bufferDuration                              // "The length of this input."
var bufferFormat                                // "The audio format of this input."
var buffer                                      // *(Deprecated)* "A new copy of the audio data
                                                //  for this input."
```
✅ VERIFIED — `/documentation/speech/analyzerinput`.

Two contract statements from that page you should read as hard rules:

> *The audio data **must** have an audio format that is supported by the analyzer's modules; **the
> analyzer does not perform audio conversion**.*
>
> *The audio format **may differ from one `AnalyzerInput` object to the next**. If the new audio
> format is supported by the modules, the modules will be reconfigured as needed.*

The second is more permissive than people expect: a session can switch formats mid-stream — a
Bluetooth headset connecting, say — as long as every format is one the modules accept.

Skipping audio is supported and documented:

> ✅ **VERIFIED**, `/documentation/speech/speechanalyzer`, verbatim: *"To skip past part of an audio
> stream, omit the buffers you want to skip from the input sequence. You can resume with a later
> buffer. When you resume analysis with a later `AVAudioPCMBuffer` buffer, you may need to supply
> the correct time-code to account for skipped audio."*

This is how you implement a pause button that does not restart the session: stop yielding, then
resume yielding with an explicit `bufferStartTime`. The analyzer's time-line stays honest and your
`.audioTimeRange` attributes still line up with the original recording, which matters if you are
also saving the audio.

⚠️ Note `var buffer` is marked **deprecated** on the `AnalyzerInput` page — read the format and
timing metadata instead of pulling a copy of the samples back out.

---

## 7. Running the analysis

### 7.1 The two-line core

```swift
let lastAudioTime = try await analyzer.analyzeSequence(audioSequence)
if let lastAudioTime {
    try await analyzer.finalizeAndFinish(through: lastAudioTime)
}
```
✅ VERIFIED — quoted verbatim from *"Recognizing speech in live audio"*, §"Analyze audio and display
results". The identical pattern (with an `else { try analyzer.cancelAndFinishNow() }` branch)
appears in the canonical example on `/documentation/speech/speechanalyzer`.

Everything about that pair repays study, because the return value is doing three jobs at once.

> ✅ **VERIFIED** — `/documentation/speech/speechanalyzer/analyzesequence(_:)`, verbatim:
>
> *The time-code of the last audio sample that was consumed from this or an earlier input sequence,
> or `nil` if no audio sample has been consumed. You may use this value for the parameter of
> `finalizeAndFinish(through:)`.*
>
> *When this method returns, **the last audio consumed from the input sequence may still be
> undergoing analysis**. To wait for the analysis to complete, call another method such as
> `finalize(through:)` and await its return.*
>
> *If you cancel the task executing this method, **most input sequences will terminate early,
> causing this method to return early. The method returns the time-code of the last audio sample
> that was consumed and does not throw `CancellationError`**.*

Job one: it is the **watermark**. "This much audio went in." Pass it to `finalizeAndFinish(through:)`
and you are saying "finalise everything up to the last thing I fed you, then end the session."

Job two: it is the **cancellation signal in disguise**. When the task running `analyzeSequence` is
cancelled, the method *returns normally with a value* rather than throwing `CancellationError`. That
is unusual and deliberate: it means the ordinary post-analysis code path — finalise, then finish —
runs identically whether the sequence ended naturally or the user hit stop. You do not need a
`catch is CancellationError` branch. **This is the design decision that makes §9 work at all.**

Job three: `nil` is the **"no audio at all"** case. The user tapped record and stop within a few
milliseconds, or the microphone was never granted. Apple's canonical example handles it with
`cancelAndFinishNow()`, which is the right instinct: there is nothing to finalise, so end the
session immediately rather than leaving the result streams open forever (§2.3).

And job zero, hiding in the second paragraph: **`analyzeSequence` returning does not mean analysis
finished.** Audio it already consumed may still be in flight. If you read `transcriber.results`
after `analyzeSequence` returns and before `finalizeAndFinish` completes, you are reading a stream
that is still producing. This is exactly the race §9 is about.

### 7.2 The task-group structure

Apple's article is explicit about the shape, and it is worth quoting in full because the *reason*
for the shape is stated:

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, §"Analyze audio and display results",
> verbatim:
>
> *The app does its primary work in the `runSession` method. This work consists of two subtasks:*
> - *Analyzing audio from the capture session*
> - *Displaying transcription updates from the transcriber module*
>
> *The app adds the subtasks to a task group in `runSession`. **The task group uses Swift's
> structured concurrency mechanism to ensure that both subtasks run to completion before
> `runSession` returns**.*

```swift
try await withThrowingDiscardingTaskGroup() { group in
    // Subtask 1: Analyze audio from the capture session
    group.addTask {
        try await self.captureAndAnalyzeAudio(
            transcriber: transcriber,
            captureSession: captureSession,
            audioSequence: audioSequence
        )
    }

    // Subtask 2: Display transcription updates from the transcriber module
    group.addTask {
        // This cancellation shield prevents the transcription update loop from immediately ending
        // when the `stopRecording()` method cancels the recording task.
        try await withTaskCancellationShield {
            try await self.updateTranscription(transcriber: transcriber)
        }
    }
}
```
✅ VERIFIED — quoted verbatim from the article, comments included.

`withThrowingDiscardingTaskGroup` is the right choice here rather than
`withThrowingTaskGroup(of: Void.self)` because neither subtask returns a value and you never want to
`next()` them; the discarding variant reaps children as they finish rather than accumulating
results, and it rethrows the first error.

The structural guarantee is the point: **`runSession` cannot return until both subtasks are done.**
So cancelling the outer recording task does not, by itself, end the recording — it starts a
shutdown that completes only when the analysis has been finalised *and* the display loop has drained
the result stream. That is what you want. It is also exactly why one of the two subtasks must
refuse to be cancelled.

### 7.3 Which `finish` method

Four of them, and the choice is not arbitrary.

| Method | Use when |
|---|---|
| `finalizeAndFinish(through:)` | **The default.** You have a watermark from `analyzeSequence` and you want everything up to it transcribed before the session ends. |
| `finalizeAndFinishThroughEndOfInput()` | Your input sequence has a natural end and you want end-of-input to mean end-of-session. Apple names it as *the* exception to "terminating the input sequence does not finish the session" (§2.3). |
| `cancelAndFinishNow()` | Nothing to finalise, or you are tearing down after an error. Note it is **not** `async` in the canonical example: `try analyzer.cancelAndFinishNow()`. |
| `finish(after:)` | You want the session to end at a specific future time-code rather than at the current watermark. |

Plus two mid-session methods that do not finish anything:

- `finalize(through:)` — "Finalizes the modules' analyses" up to a time, session continues. This is
  how you force volatile results to settle without ending the recording — useful for a "commit this
  paragraph" affordance.
- `cancelAnalysis(before:)` — "Stops analyzing audio predating the given time." Discards a backlog.
  If your app fell behind during a burst and you would rather skip than lag, this is the lever.

✅ VERIFIED — all six names and descriptions from `/documentation/speech/speechanalyzer`.

> 🟡 **RECONSTRUCTED — which of these are `async`.** Apple's index page lists the names without
> declarations; the canonical example shows `try await analyzer.finalizeAndFinish(through:)` and
> `try analyzer.cancelAndFinishNow()` — so at least those two differ. Write the `await` and let the
> compiler remove it if it is unnecessary.

### 7.4 Stopping a live capture: two approaches, one recommendation

Apple lays out both and picks one. The reasoning is the interesting part.

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, §"Stop the capture session", verbatim:
>
> *The app cancels the recording task when the user taps the stop button, but it's not the only way
> to implement the app. An alternative is to fully end the capture session, ending the audio
> sequence, after which the `analyzeSequence(_:)` method returns as in the cancellation case.
> **However, a capture session can start, stop, and restart many times, so the only way to fully end
> a capture session is to release all references to it and let it deallocate.***
>
> ***Because it's easy to overlook a stray reference, cancellation is the more reliable approach.***

That sentence — *"the only way to fully end a capture session is to release all references to it"* —
is the whole argument. `AVCaptureSession.stopRunning()` does not end a session; it pauses one. A
session that has been stopped can be started again, and the audio sequence built on top of it is
therefore not finished, merely idle. So "end the session to end the sequence" requires you to be
certain that no closure, no property, no `Task` and no SwiftUI view is holding the session — and
Swift gives you no way to assert that.

Cancellation, by contrast, is a first-class signal with a documented contract: cancel the task,
`analyzeSequence` returns early with a watermark, you finalise, the result streams terminate, both
subtasks complete, the group returns. Nothing depends on object lifetime.

**Recommendation:** cancel the task. Keep the capture session in an actor (§6.4) and release it in
a `defer` for hygiene, but do not make correctness depend on that release happening.

```swift
/// The whole stop path.
func stopRecording() {
    recordingTask?.cancel()
    // Everything else — finalisation, result drainage, session teardown — happens inside
    // runSession's task group, and `runSession` cannot return until it has.
}
```

---

## 8. Result merging: the subtle part

This is where most implementations go wrong, and it is not because the API is badly designed. It is
because the API deliberately does *not* do a thing you assume it does.

### 8.1 The module does not accumulate a transcript

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, §"Analyze audio and display results",
> verbatim:
>
> ***The transcriber module doesn't accumulate an overall transcription.** Instead, it provides a
> number of results for different audio time ranges. The app incorporates each update into an
> overall transcription and replaces the currently displayed transcription with the new one.*
>
> *Since the app uses the transcriber module's `progressiveLongDictation` preset, **some results
> replace previous results**. The app uses the audio time range of each result to determine if part
> of the overall transcript needs to be replaced.*

And from the `SpeechTranscriber.Result` page, the mechanism stated from the other side:

> ✅ **VERIFIED** — `/documentation/speech/speechtranscriber/result`, verbatim: *"If the transcriber
> is configured to send volatile results, **each phrase is sent one or more times as the
> interpretation gets better and better until it is finalized**."*

So `transcriber.results` is not a stream of new text. It is a stream of **assertions about ranges of
audio**, some of which supersede earlier assertions about overlapping ranges. Naively appending
every result to a string produces a transcript that says "I went to the — I went to the store — I
went to the store today" because you have concatenated three revisions of one phrase.

Each result carries what you need to do better:

```swift
struct SpeechTranscriber.Result   // CustomStringConvertible, Equatable, Hashable, Sendable,
                                  // SpeechModuleResult
var text: AttributedString        // "The most likely interpretation of the audio in this range."
var alternatives                  // "All the alternative interpretations of the audio in this
                                  //  range. The interpretations are in descending order of
                                  //  likelihood."
// inherited from SpeechModuleResult:
var range                         // the audio time range this result applies to
var isFinal: Bool                 // whether this result is final at the time it is produced
var resultsFinalizationTime       // results are final up to but not including this time
```
✅ VERIFIED — `/documentation/speech/speechtranscriber/result` plus the `SpeechModuleResult`
protocol.

🔴 **GAP — `DictationTranscriber.Result`.** Its own reference page was not fetched. It conforms to
`SpeechModuleResult` (so it has `range`, `isFinal`, `resultsFinalizationTime`) and Apple's article
treats it as having a text payload, but we cannot confirm whether it also has `alternatives` — and
given that `DictationTranscriber` has no `alternativeTranscriptions` reporting option, it very
plausibly does not. **Resolving this** needs `/documentation/speech/dictationtranscriber/result`.
**Safe default:** use `result.text`, `result.range` and `result.isFinal` only. Those three are
protocol-guaranteed or article-attested.

### 8.2 Strategy A — range replacement in one attributed string

This is what Apple's 2026 sample does.

```swift
if let rangeToReplace = transcript.rangeOfAudioTimeRangeAttributes(intersecting: resultTimeRange) {
    transcript.replaceSubrange(rangeToReplace, with: resultTranscript)
} else {
    transcript.append(resultTranscript)
}
```
✅ VERIFIED — quoted verbatim from *"Recognizing speech in live audio"*.

The machinery underneath is in Foundation, not Speech:

- `AttributeScopes.SpeechAttributes.TimeRangeAttribute` — *"The time range in the source audio
  corresponding to the associated transcription text."*
- `AttributeScopes.SpeechAttributes.ConfidenceAttribute` — *"A confidence level (**0–1**) of the
  associated transcription text."*
- `AttributedString.rangeOfAudioTimeRangeAttributes(intersecting:)` — *"Returns the range of the
  attributed string that is within the given time range."*

✅ VERIFIED — all three from the Foundation attribute-scope pages cross-referenced by the Speech
documentation.

**How it works.** Each result's `text` arrives with time-range attributes already attached, mapping
substrings back to audio time. You keep one `AttributedString` for the whole document. When a new
result comes in for time range *T*, you ask the document "which character range of you currently
describes audio overlapping *T*?" If there is one, you splice the new text over it. If there is not
— because this is fresh audio past the end — you append.

**Why it is attractive.** One source of truth. The document you render is the document you own.
There is no "final part" and "volatile part" to concatenate at draw time, no risk of the two
drifting, and — importantly — **edits survive**. If your UI lets the user tap a word and correct it,
the correction lives in the same string and the next volatile revision replaces only the range it
actually covers.

**What it costs.** `replaceSubrange` on an `AttributedString` is not free, and you are doing it on
every result — which, with `progressiveLongDictation`, is several times a second. For a
minute-long dictation that is fine. For a 90-minute meeting recording, the string is large, the
replacements are in the middle of it, and you are doing attributed-run surgery on the main actor.

### 8.3 ⚠️ SILENT FAILURE: strategy A silently degrades to append-only

Here is the trap, and it is a good one because Apple's own article walks straight into it.

Look again at the transcriber construction from §4.4, quoted verbatim from the same article:

```swift
return DictationTranscriber(
    locale: locale,
    contentHints: contentHints,
    transcriptionOptions: preset.transcriptionOptions,
    reportingOptions: preset.reportingOptions,
    attributeOptions: preset.attributeOptions      // ← preset is .progressiveLongDictation
)
```

Now look at the preset matrix from §4.2, also from Apple:

| Preset | `shortForm` | `.volatileResults` | `.frequentFinalization` | **`.audioTimeRange`** | `.punctuation` |
|---|---|---|---|---|---|
| `progressiveLongDictation` | No | **Yes** | No | **No** | **Yes** |

`progressiveLongDictation` does **not** include `.audioTimeRange` in its attribute options. And
`.audioTimeRange` is documented as the option that *"includes time-code attributes in a
transcription's attributed string."*

If the results carry no time-range attributes, then
`transcript.rangeOfAudioTimeRangeAttributes(intersecting:)` has nothing to match and returns `nil`
— **every single time**. Which drops you into the `else` branch. Which appends. Which means every
volatile revision of every phrase is appended to the document instead of replacing the previous
revision, and your transcript reads:

```
I went to the I went to the store I went to the store today
```

No error. No warning. No log line. A perfectly plausible-looking code path that produces garbage in
proportion to how chatty the user is.

> ⚠️ **SILENT FAILURE — `.audioTimeRange` is not in the preset you were told to use.** Two Apple
> documentation pages, read together, describe a configuration that cannot work. The article says
> "use `progressiveLongDictation` and merge by time range"; the preset page says
> `progressiveLongDictation` does not emit time ranges.

**Which page is wrong?** We cannot tell from the documentation alone, and the sample project that
would settle it is not available to us (§1.2). There are three possibilities:

1. The sample's `createDictationTranscriber` unions `.audioTimeRange` into `attributeOptions` and
   the article elided that for brevity.
2. The preset matrix is out of date and `progressiveLongDictation` does emit time ranges.
3. The sample really does append-only and nobody noticed because the demo recordings are short.

> 🔴 **GAP — the resolution of the `progressiveLongDictation` / `.audioTimeRange` conflict.**
> **Resolving this** needs either the SpokenWord project's actual source, or one run on an iOS 27
> device printing `result.text.runs` for a volatile result and checking whether a time-range
> attribute is present.
>
> **SAFE DEFAULT — and this costs you nothing, so just do it:** if you intend to use
> `rangeOfAudioTimeRangeAttributes(intersecting:)`, **explicitly union `.audioTimeRange` into your
> attribute options** rather than trusting the preset:
>
> ```swift
> attributeOptions: preset.attributeOptions.union([.audioTimeRange])
> ```
>
> Or start from `timeIndexedLongDictation`, which is the preset whose entire reason for existing is
> that column — Apple describes it as *"Configure for lengthy audio, cross-referencing words to
> time-codes."* You lose `.volatileResults` by doing that, so if you want both immediacy *and* time
> codes, the union is the right move. The `.union` is one call, it is idempotent, and it makes the
> requirement visible at the point where it matters.

Every code listing in this guide that uses strategy A does the union. That is why §6.4's
`makeTranscriber` differs from Apple's article by exactly one `.union([.audioTimeRange])` — and
that difference is annotated in place.

A defensive assertion is also cheap:

```swift
/// 🟡 Our diagnostic. Run it once on a real device during bring-up.
func assertTimeRangesPresent(_ result: some SpeechModuleResult, text: AttributedString) {
    #if DEBUG
    let probe = text.rangeOfAudioTimeRangeAttributes(intersecting: result.range)
    assert(probe != nil || text.characters.isEmpty,
           "Results carry no audio-time-range attributes — add .audioTimeRange to attributeOptions.")
    #endif
}
```

### 8.4 Strategy B — two transcripts

Apple documents the alternative in the same paragraph:

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, verbatim:
>
> *This technique is straightforward, but **another common technique is to maintain two separate
> transcriptions: one containing finalized results that won't be replaced, and another containing
> volatile results that are expected to be replaced.** When a result is final, it is added to the
> first transcript; when a result is volatile, it replaces all or part of the second transcript.
> **The overall transcript in this scenario, then, consists of the first transcript followed by the
> current second transcript.***

This is precisely what the iOS 26 sample does, and we can read that code:

```swift
                for try await case let result in transcriber.results {
                    let text = result.text
                    if result.isFinal {
                        finalizedTranscript += text
                        volatileTranscript = ""
                        updateStoryWithNewText(withFinal: text)
                    } else {
                        volatileTranscript = text
                        volatileTranscript.foregroundColor = .purple.opacity(0.4)
                    }
                }
```
✅ VERIFIED — `SwiftTranscriptionSampleApp/Recording and Transcription/Transcription.swift:66-79`
(iOS 26 sample).

Note how little there is to it. `isFinal` is the entire dispatch. There is no time-range arithmetic,
no `replaceSubrange`, no attribute dependency. And the UI affordance falls out for free: the sample
tints `volatileTranscript` purple at 40% opacity, so the user *sees* which words are still
provisional. That is a genuinely good interaction and it is three characters of code.

Rendering is `finalizedTranscript + volatileTranscript` at draw time.

### 8.5 The trade

| | **A — range replacement** | **B — two transcripts** |
|---|---|---|
| Source of truth | One `AttributedString` | Two, concatenated at render |
| Depends on `.audioTimeRange` | **Yes** — and silently no-ops without it (§8.3) | **No** — only on `isFinal` |
| Cost per result | `replaceSubrange` on the whole document | String assignment |
| Cost at 90 minutes | Grows with document size | Constant |
| Volatile styling | You must find the volatile range yourself | Free — it is a separate string |
| Survives user edits mid-recording | **Yes** — edits outside the replaced range persist | **No** — the volatile string is clobbered wholesale |
| Handles a result revising *older* audio | **Yes** — that is the whole point | **No** — assumes revisions only ever touch the tail |
| Lines of code | ~6 plus configuration care | ~8, no configuration care |
| Apple's 2026 article uses | ✅ | — |
| Apple's iOS 26 sample uses | — | ✅ |

**How to choose.** The question that decides it is: *can a result revise audio that is not at the
end of the stream?*

With `.volatileResults` alone, revisions are tail-only in practice — the engine is refining the
phrase it is currently hearing. Strategy B is correct, cheaper, and simpler. **Use B for live
dictation UI.**

With `.frequentFinalization`, multiple ranges can be in flight, and with a long-form engine doing
second-pass refinement the assumption weakens further. Strategy A is the one that is *correct by
construction* rather than correct by assumption. **Use A when you also need time-indexed output** —
captions, a scrubbing UI, word-level audio alignment, anything that will later ask "what time was
this word said?" If you are going to carry `.audioTimeRange` anyway, A costs you nothing extra
conceptually.

And Apple's own third option, which is the best one when it applies:

> ✅ **VERIFIED**, same article, verbatim: *"**If the app didn't need to provide immediate UI
> feedback, it could configure the transcriber to only provide final results, and just append each
> result to the overall transcript, further simplifying the code.**"*

Drop `.volatileResults` — use `.longDictation` or `SpeechTranscriber`'s `.transcription` — and the
whole problem evaporates. Every result is final, every result is new audio, `transcript.append(...)`
is the entire merge function. **If your feature is "transcribe this recording", not "watch me
type with my voice", take this path.** §6.5's file-transcription function does exactly that and is
15 lines shorter for it.

### 8.6 A merge implementation for strategy A

```swift
extension LiveTranscription {

    /// Strategy A. Requires `.audioTimeRange` in attributeOptions — see §8.3.
    ///
    /// ✅ The two-branch body is quoted from Apple's article; the surrounding method is ours.
    func merge(_ result: some SpeechModuleResult) {
        let resultTranscript = result.text
        let resultTimeRange = result.range

        if let rangeToReplace = transcript.rangeOfAudioTimeRangeAttributes(intersecting: resultTimeRange) {
            transcript.replaceSubrange(rangeToReplace, with: resultTranscript)
        } else {
            transcript.append(resultTranscript)
        }
    }
}
```

> 🟡 **RECONSTRUCTED — `result.text` on a generic `SpeechModuleResult`.** `text` is declared on
> `SpeechTranscriber.Result`, not on the `SpeechModuleResult` protocol, so the generic constraint
> above will not actually give you `.text`. In real code, type the parameter concretely
> (`DictationTranscriber.Result` or `SpeechTranscriber.Result`) or add your own protocol. This is
> flagged rather than silently fixed because it is the kind of thing that looks fine in a guide and
> fails at the call site.

### 8.7 A merge implementation for strategy B

```swift
@MainActor
@Observable
final class TwoTranscriptStore {
    private(set) var finalized = AttributedString()
    private(set) var volatileText = AttributedString()

    /// What you render.
    var displayed: AttributedString { finalized + volatileText }

    /// ✅ The isFinal dispatch and the volatile styling are from Apple's iOS 26 sample;
    ///    the container is ours.
    func ingest(text: AttributedString, isFinal: Bool) {
        if isFinal {
            finalized += text
            volatileText = AttributedString()
        } else {
            var styled = text
            styled.foregroundColor = .purple.opacity(0.4)
            volatileText = styled
        }
    }
}
```

Two notes. `displayed` is computed, so SwiftUI recomputes it whenever either half changes and you
never have a stale concatenation. And `foregroundColor` on an `AttributedString` requires the
SwiftUI attribute scope — `import SwiftUI` — which is why the iOS 26 sample can write
`.purple.opacity(0.4)` directly.

### 8.8 Confidence attributes

`.transcriptionConfidence` is the option no preset enables, and it is worth knowing about because
it enables an interesting UI: dimming or underlining low-confidence words so the user knows where
to look when proofreading.

> ✅ **VERIFIED** — `AttributeScopes.SpeechAttributes.ConfidenceAttribute` is described as
> *"A confidence level (0–1) of the associated transcription text."*

> 🔴 **GAP — how to read a confidence value in code.** We have the attribute type's name and
> semantics but not the key path you use to read it from an `AttributedString` run. The Speech
> attribute scope's property names were not harvested. **Resolving this** needs
> `/documentation/foundation/attributescopes/speechattributes` or Xcode autocompletion on a run's
> attribute container. **Safe default:** iterate `text.runs` and inspect the run's
> `attributes` container; the attribute you want is the one whose value is a floating-point number
> in 0…1. Do not hardcode a key path from a guide — including this one.

---

## 9. ⚠️ The cancellation shield

If you read one section of this guide, read this one. It is the defect that costs you the last
sentence of every recording, it produces no error of any kind, and the bug report you will get is
"sometimes it cuts off the end", which is unfalsifiable in the field and irreproducible in a demo.

### 9.1 The failure

Apple states it in a single sentence, and the sentence is easy to skim past:

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, §"Stop the capture session", verbatim:
>
> *The second subtask (which displays transcriptions) is shielded from cancellation and so it
> continues reading from the results sequence until it reads the final update and finds the end of
> the sequence, at which point the app finishes that subtask. **Without the cancellation shield, the
> second subtask stops reading the sequence immediately, before the transcriber module adds its
> final updates.***

Read that last clause again. *Before the transcriber module adds its final updates.* Not "before it
finishes cleanly" — before the **final** results exist. The words the user just said, the ones
still being finalised when they hit stop, are produced *after* cancellation and read by nobody.

### 9.2 Why the two subtasks have opposite requirements

Cancellation in Swift is **cooperative**. `Task.cancel()` sets a flag; it does not stop anything.
Code stops because it checks the flag, or because it is suspended inside something that checks the
flag on its behalf — and `for try await` on an `AsyncSequence` is very much in the second category.
Cancel the enclosing task and most async sequences terminate at the next suspension point.

Now put the two subtasks side by side.

**Subtask 1 — analyzing.** It sits in `try await analyzer.analyzeSequence(audioSequence)`, waiting
for microphone audio that will never stop arriving on its own. **It must be cancellable**, because
cancellation is the *only* thing that will ever make it return. And Apple designed
`analyzeSequence` to make that clean:

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, verbatim:
>
> *In the first subtask (which analyzes audio), the canceled `analyzeSequence(_:)` method
> **immediately stops analyzing additional audio and returns**, and then the app calls
> `finalizeAndFinish(through:)` to get a final update and end the analysis. **After the transcriber
> module adds that final update to its `results` sequence, it terminates the sequence.** Then the
> app stops the capture session and finishes that subtask.*

So subtask 1's *response to cancellation* is to produce the final results. Cancellation is not an
abort here; it is the trigger for an orderly finish. This works because `analyzeSequence` returns a
watermark instead of throwing `CancellationError` (§7.1), so the finalisation code runs on the
normal path.

**Subtask 2 — displaying.** It sits in `for try await result in transcriber.results`. **It must
survive cancellation**, because the results it exists to read are *produced by subtask 1's
cancellation handling*. If it dies when the flag is set, it is gone before the thing it is waiting
for is created.

```
   user taps Stop
        │
        ▼
   recordingTask.cancel()          ← sets the flag on both subtasks
        │
        ├──────────────► SUBTASK 1 (must be cancellable)
        │                  analyzeSequence returns early, with watermark
        │                  finalizeAndFinish(through: watermark)
        │                       └─► transcriber emits FINAL results ──┐
        │                       └─► transcriber terminates .results ──┤
        │                  stop capture session                       │
        │                  subtask 1 done                             │
        │                                                             │
        └──────────────► SUBTASK 2 (must NOT be cancellable)          │
                           for try await result in transcriber.results│
                           ◄──────────────────────────────────────────┘
                           …still reading. Gets the final results.
                           Sequence ends. Subtask 2 done.
                                                  │
   withThrowingDiscardingTaskGroup returns ◄──────┘
```

Without the shield, the right-hand column collapses: subtask 2 exits at the moment of cancellation,
subtask 1 goes on to produce final results into a stream nobody is reading, and the transcript on
screen is missing whatever was volatile at the moment the user tapped stop. Which, for the
`progressiveLongDictation` preset, is **the entire current phrase**.

### 9.3 Why this is a *silent* failure specifically

Every element of this conspires to hide:

- **Nothing throws.** Cancelling a task that ends normally is not an error. The group completes.
  `runSession` returns. Your `catch` never fires.
- **The transcript is not empty**, just short. Short by an amount that scales with how fast the user
  was talking and how quickly they hit stop.
- **It does not reproduce when you test it.** The way developers test dictation is: tap record, say
  "testing one two three", pause, tap stop. That pause is enough for the engine to finalise, so the
  final result arrives *before* cancellation and the bug does not appear. It appears for users who
  stop talking and stop recording in the same motion — which is what everyone does in real life.
- **It looks like a model quality issue.** "The transcription cut off" reads as ASR failure, not
  as a concurrency bug, so it gets triaged to the wrong place.

This is a textbook instance of the property this whole series is about: **the defect does not
throw.** The API is correct, your code compiles, the types check, and the output is quietly wrong.

### 9.4 What `withTaskCancellationShield` actually is

> 🔴 **GAP — the provenance of `withTaskCancellationShield`.** It appears in Apple's article code
> block, in a comment written by Apple, and **nowhere else in our corpus** — not in the Speech
> framework symbol index, not in the iOS 26 sample, not in any other documentation page we fetched.
> It is therefore one of:
>
> - a Swift concurrency library function (in which case it is a Swift-evolution addition, not a
>   Speech API, and belongs to the toolchain rather than the SDK);
> - a helper defined inside the SpokenWord sample project, which we cannot read (§1.2).
>
> **Resolving this** takes one line in a scratch Swift file on a machine with the Swift 6.x
> toolchain that ships with Xcode 27: type the name and see whether it resolves.
>
> **SAFE DEFAULT — write it yourself.** The semantics are unambiguous ("run this child work in a
> context where the parent's cancellation flag is not visible"), and an unstructured `Task` already
> has exactly that property: a `Task { }` created inside another task does *not* inherit
> cancellation. So:

```swift
/// Runs `body` in a context that does not observe the calling task's cancellation.
///
/// 🟡 OUR IMPLEMENTATION of the semantics Apple's article describes. If
/// `withTaskCancellationShield` resolves in your toolchain, prefer Apple's — the name in the
/// article is the one to search for first.
///
/// The mechanism: an unstructured `Task` does not inherit the cancellation state of the task
/// that created it. Awaiting its `value` re-suspends the caller, but the child keeps running
/// even after the parent is cancelled.
func withTaskCancellationShield<T: Sendable>(
    _ body: @escaping @Sendable () async throws -> T
) async throws -> T {
    let shielded = Task { try await body() }
    return try await shielded.value
}
```

Two caveats on that implementation, stated plainly because they are real:

1. **`await shielded.value` is itself cancellable.** If the caller is cancelled, the `await` throws
   `CancellationError` *in the caller* while the child continues to completion in the background.
   For the Speech use case that is acceptable — the child's job is to finish reading and update the
   UI, and it will — but it means the enclosing task group may return before the child is done,
   weakening the structured-concurrency guarantee §7.2 relies on. If you need the group to genuinely
   wait, hold the `Task` handle outside the group and await it after the group returns.
2. **It escapes structured concurrency**, so the child does not inherit task-local values or the
   parent's priority. Neither matters here; both would matter in other contexts.

Given caveat 1, the version worth shipping keeps the handle:

```swift
/// A shape that preserves the "both finished before we return" guarantee.
///
/// 🟡 Ours. Same semantics, structured differently: the display loop runs in an unstructured
/// task (immune to cancellation), and we await it *after* the analyzing task group completes.
private func runSession(...) async throws {
    // …module, analyzer and provider setup as in §6.4…

    // Unstructured: does not inherit cancellation from `recordingTask`.
    let displayTask = Task { [weak self] in
        guard let self else { return }
        for try await result in transcriber.results {
            await MainActor.run { self.merge(result) }
        }
    }

    // Cancellable: this is the one that must respond to `stopRecording()`.
    do {
        try await captureAndAnalyzeAudio(analyzer: analyzer,
                                         audioSequence: provider.analyzerInputs)
    } catch {
        displayTask.cancel()   // real error: tear the reader down too
        throw error
    }

    // By now finalizeAndFinish has run, the module has emitted its final results and
    // terminated `results`, so this await returns promptly — and it is NOT skipped by
    // cancellation, because we reach it on the normal path (analyzeSequence does not
    // throw CancellationError). ✅ per /documentation/speech/speechanalyzer/analyzesequence(_:)
    _ = try await displayTask.value
}
```

> ⚠️ **Do not "fix" this by adding `Task.checkCancellation()` to the display loop.** That is the
> opposite of what you need. The display loop's whole job is to *ignore* cancellation until the
> sequence ends on its own. The sequence ending is the termination condition; the cancellation flag
> is not.

### 9.5 The test that catches it

Because a human tester cannot reliably reproduce this, automate the timing:

```swift
/// 🟡 Ours. Run on a device (the Simulator will not capture audio — §"What you need").
///
/// The bug appears when cancellation arrives while a volatile result is outstanding.
/// Feed known audio, cancel immediately at the end of speech, and assert the tail survived.
func testTailSurvivesImmediateStop() async throws {
    let store = TwoTranscriptStore()
    let controller = LiveTranscription()

    controller.startRecording()
    try await playFixtureAudio("the quick brown fox jumps over the lazy dog")
    // No settle time. This is the point.
    controller.stopRecording()

    try await controller.waitUntilFinished()

    #expect(String(store.displayed.characters).lowercased().contains("lazy dog"))
}
```

The assertion to write is *"contains the last few words"*, not *"equals the expected string"* — ASR
output varies and you want the test to fail for the concurrency reason, not for a punctuation
difference. If `lazy dog` is missing while `quick brown fox` is present, you have this bug.

---

## 10. A complete worked example

§6.4 gave the microphone pipeline using Apple's own composition — a task group with
`withTaskCancellationShield` and strategy-A merging. This section gives the **alternative
composition**: the self-implemented shield from §9.4, strategy-B merging from §8.4, and a SwiftUI
view on top. Both are correct. This one has fewer unresolved gaps in it, which is why it is the one
to start from if you want something running today.

Every Speech, AVFoundation and Foundation call below is ✅ VERIFIED against an Apple page or sample.
Structure, naming and error handling are ours. Provenance is annotated inline.

```swift
//  LiveDictation.swift
//  Requires: iOS 27 / iPadOS 27 / macOS 27 (physical device — not the Simulator)

import Speech
import AVFoundation
import CoreMedia
import SwiftUI
import Observation

// MARK: - Errors

enum DictationError: Error, LocalizedError {
    case localeNotSupported(Locale)
    case couldNotCaptureMicrophone
    case micPermissionDenied

    var errorDescription: String? {
        switch self {
        case .localeNotSupported(let l):
            return "Dictation is not available for \(l.identifier(.bcp47))."
        case .couldNotCaptureMicrophone:
            return "No microphone is available."
        case .micPermissionDenied:
            return "Microphone access was denied."
        }
    }
}

// MARK: - Capture session ownership
//
// Apple: "To avoid concurrency-related compilation errors, the app actually saves the session
// instance in an actor and manages the session through that actor."
// ✅ VERIFIED — "Recognizing speech in live audio", §"Configure the capture session".

actor CaptureSessionBox {
    private var session: AVCaptureSession?

    func adopt(_ session: AVCaptureSession) { self.session = session }
    func start() { session?.startRunning() }

    /// Apple: "the only way to fully end a capture session is to release all references to it
    /// and let it deallocate." ✅ VERIFIED, §"Stop the capture session".
    /// We do this for hygiene; correctness rests on task cancellation, not on this call.
    func release() {
        session?.stopRunning()
        session = nil
    }
}

// MARK: - Transcript store (strategy B — §8.4)

@MainActor
@Observable
final class TranscriptStore {
    private(set) var finalized = AttributedString()
    private(set) var volatileText = AttributedString()

    var displayed: AttributedString { finalized + volatileText }
    var plainText: String { String(displayed.characters) }

    /// ✅ The isFinal dispatch and the volatile tinting are Apple's, from the iOS 26 sample
    ///    (Transcription.swift:66-79). The container is ours.
    func ingest(_ text: AttributedString, isFinal: Bool) {
        if isFinal {
            finalized += text
            volatileText = AttributedString()
        } else {
            var styled = text
            styled.foregroundColor = .secondary
            volatileText = styled
        }
    }

    func reset() {
        finalized = AttributedString()
        volatileText = AttributedString()
    }
}

// MARK: - The controller

@MainActor
@Observable
final class LiveDictation {

    let store = TranscriptStore()

    private(set) var isRecording = false
    private(set) var lastError: Error?
    private(set) var downloadProgress: Progress?

    private let sessionBox = CaptureSessionBox()
    private var recordingTask: Task<Void, Never>?

    private let locale: Locale
    private var lmConfiguration: SFSpeechLanguageModel.Configuration?

    init(locale: Locale = .current) {
        self.locale = locale
    }

    // ── Step 1: build the module ───────────────────────────────────────────
    //
    // ✅ Body quoted from Apple's article, §"Configure the speech analyzer" — with one
    //    deliberate change: `.union([.audioTimeRange])` is NOT added here, because
    //    strategy B does not need time ranges (§8.3, §8.5). If you switch to strategy A,
    //    add it.

    private func makeTranscriber(locale matched: Locale) -> DictationTranscriber {
        let preset = DictationTranscriber.Preset.progressiveLongDictation

        let contentHints = if let lmConfiguration {
            preset.contentHints.union([.customizedLanguage(modelConfiguration: lmConfiguration)])
        } else {
            preset.contentHints
        }

        return DictationTranscriber(
            locale: matched,
            contentHints: contentHints,
            transcriptionOptions: preset.transcriptionOptions,
            reportingOptions: preset.reportingOptions,
            attributeOptions: preset.attributeOptions
        )
    }

    // ── Step 2: assets and permission ──────────────────────────────────────
    //
    // Ordering is load-bearing: assets, then format, then analyzer, then audio (§5.5).

    func prepare(customLanguageModel configuration: SFSpeechLanguageModel.Configuration? = nil) async throws {
        self.lmConfiguration = configuration

        guard let matched = await DictationTranscriber.supportedLocale(equivalentTo: locale) else {
            throw DictationError.localeNotSupported(locale)
        }

        // A throwaway module is fine: "the system installs assets using the modules'
        // configuration, not their object identity." ✅ VERIFIED, AssetInventory.
        let probe = makeTranscriber(locale: matched)

        // ⚠️ Returns nil when already installed. Never force-unwrap (§5.3).
        if let request = try await AssetInventory.assetInstallationRequest(supporting: [probe]) {
            downloadProgress = request.progress      // ProgressReporting → bind to ProgressView
            defer { downloadProgress = nil }
            try await request.downloadAndInstall()
        }

        // ✅ VERIFIED call, quoted from the article, §"Prepare to record and transcribe speech".
        guard await AVCaptureDevice.requestAccess(for: .audio) else {
            throw DictationError.micPermissionDenied
        }
    }

    // ── Start / stop ───────────────────────────────────────────────────────

    func start() {
        guard !isRecording else { return }
        isRecording = true
        lastError = nil
        store.reset()

        recordingTask = Task { [weak self] in
            guard let self else { return }
            do {
                try await self.runSession()
            } catch is CancellationError {
                // Normal stop. Not an error.
            } catch {
                await MainActor.run { self.lastError = error }
            }
            await MainActor.run { self.isRecording = false }
        }
    }

    /// Apple: "When the user taps the Stop Recording button, the app simply cancels that task."
    /// ✅ VERIFIED, §"Stop the capture session". Cancellation is preferred over ending the
    /// capture session because "it's easy to overlook a stray reference".
    func stop() {
        recordingTask?.cancel()
    }

    /// For tests: wait for a full, clean shutdown.
    func waitUntilFinished() async {
        await recordingTask?.value
    }

    // ── The session ────────────────────────────────────────────────────────

    private func runSession() async throws {
        guard let matched = await DictationTranscriber.supportedLocale(equivalentTo: locale) else {
            throw DictationError.localeNotSupported(locale)
        }

        // Step 1: modules.
        let transcriber = makeTranscriber(locale: matched)
        let modules: [any SpeechModule] = [transcriber]

        // Step 4: analyzer.
        let analyzer = SpeechAnalyzer(modules: modules)

        // Step 3: input sequence — the 2026 path.
        // ✅ Both lines quoted from the article, §"Configure the capture session".
        guard let captureDevice = AVCaptureDevice.default(.microphone,
                                                          for: .audio,
                                                          position: .unspecified) else {
            throw DictationError.couldNotCaptureMicrophone
        }
        let provider = try await CaptureInputSequenceProvider.providerWithSession(
            from: captureDevice,
            compatibleWith: modules
        )
        await sessionBox.adopt(provider.captureSession)

        // ── Subtask 2, started FIRST and unstructured. ──────────────────────
        //
        // ⚠️ THE CANCELLATION SHIELD (§9). An unstructured `Task` does not inherit the
        //    parent's cancellation, so this loop keeps reading after `stop()` — which is
        //    exactly when the final results are produced. Without this, the last phrase
        //    of every recording is silently lost.
        let displayTask = Task { [store] in
            for try await result in transcriber.results {
                let text = result.text
                let isFinal = result.isFinal
                await MainActor.run { store.ingest(text, isFinal: isFinal) }
            }
        }

        // ── Subtask 1, cancellable. ────────────────────────────────────────
        do {
            await sessionBox.start()
            defer { Task { await self.sessionBox.release() } }

            // ✅ Both lines quoted from the article, §"Analyze audio and display results".
            // Cancelling this task makes analyzeSequence return early WITH a watermark —
            // it does not throw CancellationError — so finalisation runs on the normal path.
            let lastAudioTime = try await analyzer.analyzeSequence(provider.analyzerInputs)
            if let lastAudioTime {
                try await analyzer.finalizeAndFinish(through: lastAudioTime)
            } else {
                // No audio was ever consumed. Nothing to finalise — but the result streams
                // must still be terminated or the display task hangs forever (§2.3).
                try analyzer.cancelAndFinishNow()
            }
        } catch {
            displayTask.cancel()
            throw error
        }

        // finalizeAndFinish has emitted the final results and terminated `results`,
        // so this returns promptly. Reaching it is guaranteed because the path above
        // does not throw on cancellation.
        _ = try await displayTask.value
    }
}

// MARK: - UI

struct DictationView: View {
    @State private var dictation = LiveDictation()

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            if let progress = dictation.downloadProgress {
                ProgressView(progress)
                    .padding(.bottom, 8)
            }

            ScrollView {
                Text(dictation.store.displayed)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }

            if let error = dictation.lastError {
                Text(error.localizedDescription)
                    .font(.footnote)
                    .foregroundStyle(.red)
            }

            Button(dictation.isRecording ? "Stop Recording" : "Start Recording") {
                if dictation.isRecording {
                    dictation.stop()
                } else {
                    dictation.start()
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
        .task {
            do {
                try await dictation.prepare()
            } catch {
                // Surface it; do not silently degrade — a missing asset means no transcription.
            }
        }
    }
}
```

### 10.1 What to change for each variation

| You want | Change |
|---|---|
| Time-indexed output (captions, scrubbing) | Add `.union([.audioTimeRange])` to `attributeOptions` and switch to strategy A (§8.2, §8.6) |
| Batch transcription of a file | Replace `CaptureInputSequenceProvider` with `AssetInputSequenceProvider` and drop the shield entirely (§6.5) |
| Best accuracy, no live feedback | `DictationTranscriber.Preset.longDictation` (or `SpeechTranscriber` `.transcription`); every result is final, merge becomes `append` (§8.5) |
| Alternatives / editing suggestions | `SpeechTranscriber` with `.transcriptionWithAlternatives` — and give up custom vocabulary (§3.4) |
| Custom vocabulary | §11, then pass the `Configuration` to `prepare(customLanguageModel:)` |
| Power saving in long silences | Add a `SpeechDetector` module (§12) |
| Multiple concurrent analyzers | Read §13.1 first — there is a hard system limit |

### 10.2 Verification checklist before you ship this

Because so much of the above is documentation-derived rather than sample-derived, run this list on
a real iOS 27 device once. Each item takes a minute and each one closes a gap in §15.

1. `print(AssetInventory.maximumReservedLocales)` — gap G5.
2. Type `withTaskCancellationShield` in a scratch file. Does it resolve? — gap G6.
3. `let x = provider.captureAudioDataOutput` and option-click the type — gap G4.
4. Print `result.text.runs` for a **volatile** result from `progressiveLongDictation` and check
   whether a time-range attribute is present — gap G1, the §8.3 conflict.
5. Record, speak, and hit stop **mid-word**. Is the last word present? — §9.5.
6. Airplane mode on a device that has never transcribed. Does `prepare()` fail with a useful error?
7. `print(AssetInventory.status(forModules: [t]))` before and after install — gap G2 (`Comparable`
   ordering).

---

## 11. Custom vocabulary and custom language models

### 11.1 The three levers, ranked by cost

§4.4 listed them; here is when each is actually right.

**Lever 1 — `AnalysisContext.contextualStrings`.** Free, runtime, per-session.

```swift
final class AnalysisContext                 // iOS 26.0+
var contextualStrings                       // bias words
```
✅ VERIFIED — `/documentation/speech/analysiscontext`. Apple: *"To bias recognition towards certain
words, create an `AnalysisContext` object and add those words to its `contextualStrings` property.
Create a `SpeechAnalyzer` instance with that context object or set the analyzer's `context`
property."*

This is the one to reach for **first**, and most apps never need anything else. The names in the
user's contact list, the titles in their library, the items on the screen right now — push those in
and recognition of them improves. It costs nothing, it changes per session, and it needs no build
tooling.

> 🔴 **GAP — how many contextual strings is too many, and the type of `contextualStrings`.** Not
> published. It is presumably `[String]`. There is no documented limit and no documented behaviour
> when the list is large. **Safe default:** keep it in the low hundreds and prioritise — put the
> names actually visible on screen at the front, not the user's entire address book.

**Lever 2 — content hints.** Free, one line. `.farField`, `.atypicalSpeech`, `.shortForm`. Covered
in §4.4.

**Lever 3 — a custom language model.** This is the rest of §11. It requires an offline build step
that produces a binary file, that file shipped in your app bundle, and a preparation call at
launch. It is genuinely heavier than the other two, and it is the only one that can teach the engine
words it has never heard and pronunciations it cannot guess.

**Use lever 3 when** your domain vocabulary is (a) large, (b) fixed at build time, and (c)
phonetically unusual — chess openings, drug names, aircraft registrations, chemical compounds,
surnames from a language other than the transcription locale. **Do not use it** for a handful of
words that change per session; that is lever 1.

⚠️ And the constraint that decides eligibility: **lever 3 works only with `DictationTranscriber`.**
`SpeechTranscriber` has no `ContentHint`. If your feature needs alternatives *and* custom
vocabulary, you cannot have both from one module.

### 11.2 The three-stage pipeline

> ✅ **VERIFIED** — *"Recognizing speech in live audio"*, §"Customize the language model", verbatim:
>
> *Developers can enhance the `DictationTranscriber` transcriber module for specific use cases and
> applications by customizing its language model… The high-level steps in this process are:*
> - *Training data generation*
> - *Training data preparation*
> - *Transcriber configuration*

Concretely:

```
  ┌──────────────────────────────────────────────────────────────┐
  │ STAGE 1 — build time, on your Mac                            │
  │                                                              │
  │  A command-line target you write                             │
  │    └─ SFCustomLanguageModelData(locale:identifier:version:) { │
  │         PhraseCount(...)                                     │
  │         PhraseCountsFromTemplates(classes:) { Template(...) } │
  │         CustomPronunciation(grapheme:phonemes:)              │
  │       }                                                      │
  │    └─ .export(to: url)   ──────────►  CustomLMData (en_US).bin│
  └───────────────────────────────┬──────────────────────────────┘
                                  │  ship the .bin in your app bundle
  ┌───────────────────────────────▼──────────────────────────────┐
  │ STAGE 2 — app launch, on device                              │
  │                                                              │
  │  SFSpeechLanguageModel.prepareCustomLanguageModel(           │
  │      for: <the exported data>,                               │
  │      configuration: lmConfiguration)                         │
  └───────────────────────────────┬──────────────────────────────┘
                                  │
  ┌───────────────────────────────▼──────────────────────────────┐
  │ STAGE 3 — every transcriber you create                       │
  │                                                              │
  │  contentHints: preset.contentHints.union([                   │
  │      .customizedLanguage(modelConfiguration: lmConfiguration)│
  │  ])                                                          │
  └──────────────────────────────────────────────────────────────┘
```

Apple's article confirms the tooling shape:

> ✅ **VERIFIED**, verbatim: *"This sample includes a command-line utility named `datagenerator`
> that generates a training data file, and includes the file itself (named
> `CustomLMData (en_US).bin`) in the sample app's bundle. The `datagenerator` utility uses
> `SFCustomLanguageModelData` to generate this file from training data described by its result
> builder DSL."*

Note the filename convention: `CustomLMData (en_US).bin` — **the locale is in the filename**,
because a custom language model is locale-specific. A multi-language app ships one blob per locale.

⚠️ `datagenerator` is **the sample's own executable target**, not an Apple-provided tool. There is
no `xcrun` command, no build phase, and nothing in Xcode that does this for you. You write the CLI.
And per §1.2, **the sample containing it is not available to us**, so its exact structure is
unverified — but the pieces it uses are all documented types you can assemble yourself, which is
what §11.4 does.

### 11.3 The `SFCustomLanguageModelData` DSL

```swift
class SFCustomLanguageModelData            // iOS 17.0+, macOS 14.0+, visionOS 1.1+
                                           // Codable, Equatable, Hashable

init(locale:identifier:version:builder:)   // result-builder form
init(locale:identifier:version:)           // empty container

@resultBuilder SFCustomLanguageModelData.DataInsertableBuilder
@resultBuilder SFCustomLanguageModelData.TemplateInsertableBuilder

// Vocabulary and pronunciation
func insert(term:)                         // "Add a custom term to the vocabulary."
static func supportedPhonemes(locale:)     // "List the supported subset of X-SAMPA
                                           //  pronunciations supported by this locale"
struct SFCustomLanguageModelData.CustomPronunciation

// Training data
func insert(phraseCount:)                  // "Add a sample to the body of training data."
struct SFCustomLanguageModelData.PhraseCount
    // "A phrase used to bias the language model, along with a weight influencing the
    //  relative strength of the bias."

struct SFCustomLanguageModelData.PhraseCountsFromTemplates
class SFCustomLanguageModelData.TemplatePhraseCountGenerator
class SFCustomLanguageModelData.PhraseCountGenerator      // "Abstract base class"
func insert(phraseCountGenerator:)

// Output
func export(to:) async throws              // "Export the accumulated data to a file."

var identifier, locale, version

protocol DataInsertable
protocol TemplateInsertable
class SFCustomLanguageModelData.CompoundTemplate         // "You are not intended to use this
                                                         //  directly."
```
✅ VERIFIED — `/documentation/speech/sfcustomlanguagemodeldata`, `/datainsertable`,
`/templateinsertable`.

Three insertion mechanisms, three purposes.

**`PhraseCount` — exact phrases with weights.**

```swift
SFCustomLanguageModelData.PhraseCount(phrase: "Play the Albin counter gambit", count: 10)
```
✅ VERIFIED — verbatim from Apple's article.

`count:` is a weight, not a repetition instruction. Apple's own description calls it *"a weight
influencing the relative strength of the bias."* Higher means the engine is more willing to hear
this phrase in ambiguous audio. That is a real trade: bias a phrase too hard and you will start
transcribing *other* things as that phrase.

**`PhraseCountsFromTemplates` — combinatorial expansion.**

```swift
SFCustomLanguageModelData.PhraseCountsFromTemplates(classes: [
    "piece": ["pawn", "rook", "knight", "bishop", "queen", "king"],
    "royal": ["queen", "king"],
    "rank": Array(1...8).map({ String($0) })
]) {
    SFCustomLanguageModelData.TemplatePhraseCountGenerator.Template(
        "<piece> to <royal> <piece> <rank>",
        count: 10_000
    )
}
```
✅ VERIFIED — verbatim from Apple's article.

This is the feature that makes custom language models practical. `classes:` is a dictionary from a
placeholder name to its members; the `Template` string uses `<placeholder>` syntax; and the
generator expands the cross-product. The chess template above expands to
6 × 2 × 6 × 8 = **576 phrases** from four lines of source. Apple's *"training data generator can
also define phrases using templates, which expand automatically to provide a large number of exact
phrases."*

Note `count: 10_000` on a template that expands to 576 phrases.

> 🔴 **GAP — whether a template's `count:` is per-expansion or divided across expansions.** Apple
> does not say. `10_000` on a template producing 576 phrases is either a very strong bias applied
> 576 times or a budget split between them, and the difference matters a lot for how you tune.
> **Resolving this** would need either Apple documentation that does not currently exist or an
> A/B recognition experiment. **Safe default:** treat template counts as *relative* weights within
> your own data file — pick one scale and stay on it — and tune empirically against real recordings
> rather than reasoning about absolute magnitudes.

**`CustomPronunciation` — teaching the engine to say a word it has never seen.**

```swift
SFCustomLanguageModelData.CustomPronunciation(grapheme: "Winawer", phonemes: ["w I n aU @r"])
SFCustomLanguageModelData.CustomPronunciation(grapheme: "Tartakower", phonemes: ["t A r t @ k aU @r"])

SFCustomLanguageModelData.PhraseCount(phrase: "Play the Winawer variation", count: 10)
SFCustomLanguageModelData.PhraseCount(phrase: "Play the Tartakower", count: 10)
```
✅ VERIFIED — verbatim from Apple's article.

Notice the pairing: a pronunciation **and** phrase counts using the word. The pronunciation teaches
the acoustic model how the grapheme sounds; the phrase counts teach the language model that the word
occurs in this context. You want both. A pronunciation with no phrase counts gives the engine a
word it can hear but does not expect.

The phoneme strings are **X-SAMPA**, and the supported subset is per-locale:

> ✅ **VERIFIED** — `/documentation/speech/sfcustomlanguagemodeldata`: pronunciations use X-SAMPA,
> and `static func supportedPhonemes(locale:)` is documented as *"List the supported subset of
> X-SAMPA pronunciations supported by this locale."*

`"w I n aU @r"` is space-separated X-SAMPA: `w` `I` `n` `aU` `@` `r` — "wi-NOW-er". `@` is schwa,
`aU` is the "ow" diphthong. Note `phonemes:` takes an **array** of strings — multiple accepted
pronunciations for one grapheme, which is how you handle a name that half your users say
differently.

⚠️ **Validate against `supportedPhonemes(locale:)` at build time, in your CLI.** An unsupported
phoneme symbol is a data error you want to catch on your Mac, not a silently-ignored pronunciation
you discover from a support ticket. This is a two-line check and there is no reason not to do it:

```swift
// 🟡 Ours. `supportedPhonemes(locale:)` is ✅ VERIFIED; the validation loop is not Apple's.
let allowed = Set(try await SFCustomLanguageModelData.supportedPhonemes(locale: locale))
for pronunciation in myPronunciations {
    for phonemeString in pronunciation.phonemes {
        for symbol in phonemeString.split(separator: " ") {
            precondition(allowed.contains(String(symbol)),
                         "X-SAMPA symbol '\(symbol)' is not supported for \(locale.identifier).")
        }
    }
}
```

> 🔴 **GAP — the return type of `supportedPhonemes(locale:)`, and whether it is `async`.** Documented
> only by its one-line description. The `Set<String>` reading above is inference. **Safe default:**
> bind with `let allowed = try await SFCustomLanguageModelData.supportedPhonemes(locale: locale)`
> and let the compiler tell you the shape. Since this runs in *your* build-time CLI, getting it
> wrong costs a compile error, not a shipping bug.

### 11.4 Stage 1: the generator CLI

Apple's sample calls its target `datagenerator`. Here is the shape, assembled from the documented
API. This is a **macOS command-line target in your Xcode project** — add it once, run it whenever
your vocabulary changes, commit the `.bin`.

```swift
//  datagenerator/main.swift
//  A macOS command-line target. Run on your Mac; commit the output.
//
//  🟡 ASSEMBLED BY US. Every type and initializer is ✅ VERIFIED from
//     /documentation/speech/sfcustomlanguagemodeldata, and the three DSL fragments are
//     quoted verbatim from Apple's article. The surrounding program is not Apple's — the
//     sample's own `datagenerator` source is not available to us (§1.2).

import Foundation
import Speech

let locale = Locale(identifier: "en_US")
let outputURL = URL(fileURLWithPath: "CustomLMData (en_US).bin")

let data = SFCustomLanguageModelData(
    locale: locale,
    identifier: "com.example.chess",     // your app's model identifier
    version: "1.0"
) {
    // ── Exact phrases ──────────────────────────────────────────────────────
    SFCustomLanguageModelData.PhraseCount(phrase: "Play the Albin counter gambit", count: 10)
    SFCustomLanguageModelData.PhraseCount(phrase: "Play the Winawer variation", count: 10)
    SFCustomLanguageModelData.PhraseCount(phrase: "Play the Tartakower", count: 10)

    // ── Templated expansion: 6 × 2 × 6 × 8 = 576 phrases from one template ─
    SFCustomLanguageModelData.PhraseCountsFromTemplates(classes: [
        "piece": ["pawn", "rook", "knight", "bishop", "queen", "king"],
        "royal": ["queen", "king"],
        "rank": Array(1...8).map({ String($0) })
    ]) {
        SFCustomLanguageModelData.TemplatePhraseCountGenerator.Template(
            "<piece> to <royal> <piece> <rank>",
            count: 10_000
        )
    }

    // ── Pronunciations for words the engine cannot guess ───────────────────
    SFCustomLanguageModelData.CustomPronunciation(grapheme: "Winawer", phonemes: ["w I n aU @r"])
    SFCustomLanguageModelData.CustomPronunciation(grapheme: "Tartakower", phonemes: ["t A r t @ k aU @r"])
}

try await data.export(to: outputURL)
print("Wrote \(outputURL.path)")
```

> 🟡 **RECONSTRUCTED — the `identifier:` and `version:` values.** Apple documents both as
> properties and as initializer parameters, but publishes no guidance on their format or on what
> the system does with them. A reverse-DNS identifier and a semantic version are conventional and
> harmless. **What we do not know** is whether changing `version` invalidates a cached prepared
> model on device — see the `ignoresCache:` parameter in §11.5, which strongly suggests caching is
> keyed on *something*. **Safe default:** bump `version` whenever the data changes, so that if the
> cache is keyed on it, you get the new data.

> 🟡 **RECONSTRUCTED — the result-builder usage.** `init(locale:identifier:version:builder:)` is
> ✅ VERIFIED as an initializer, and `DataInsertableBuilder` / `TemplateInsertableBuilder` are
> ✅ VERIFIED as `@resultBuilder` types, and `PhraseCount` / `PhraseCountsFromTemplates` /
> `CustomPronunciation` are ✅ VERIFIED as the item types Apple uses in exactly this position.
> What is **not** verified is that mixing all three item kinds in one builder block is legal —
> `DataInsertable` and `TemplateInsertable` are two different protocols, and
> `PhraseCountsFromTemplates` takes its own nested `TemplateInsertableBuilder` closure (as shown).
> **Safe default:** if the mixed block does not compile, fall back to the imperative form, which is
> unambiguous:
>
> ```swift
> let data = SFCustomLanguageModelData(locale: locale, identifier: "…", version: "1.0")
> data.insert(phraseCount: .init(phrase: "Play the Albin counter gambit", count: 10))
> data.insert(term: "Winawer")
> data.insert(phraseCountGenerator: someGenerator)
> try await data.export(to: outputURL)
> ```
>
> All four of those methods are ✅ VERIFIED members. `SFCustomLanguageModelData` is a `class`, so
> mutation through a `let` binding is fine.

**Wire it into your build.** Two reasonable options:

1. **Commit the `.bin`.** Run the CLI by hand when vocabulary changes, check the output into the
   repo, add it to the app target's Copy Bundle Resources. Simple, reproducible, no build-time
   dependency. This is what Apple's sample does — the article says the sample "includes the file
   itself… in the sample app's bundle."
2. **A Run Script build phase** that executes the CLI into `$DERIVED_FILE_DIR`. Cleaner in
   principle; slower every build, and it puts an `async` command-line tool in your critical path.

**Prefer option 1.** Vocabulary changes rarely; builds happen constantly.

### 11.5 Stage 2: preparing the model on device

```swift
class SFSpeechLanguageModel                // iOS 17.0+, macOS 14.0+ — NO tvOS
                                           // inherits NSObject

static func prepareCustomLanguageModel(for:configuration:completion:)
static func prepareCustomLanguageModel(for:configuration:ignoresCache:completion:)

// *(Deprecated)* — migrate off these:
static func prepareCustomLanguageModel(for:clientIdentifier:configuration:completion:)
static func prepareCustomLanguageModel(for:clientIdentifier:configuration:ignoresCache:completion:)

struct/class SFSpeechLanguageModel.Configuration
    // "An object describing the location of a custom language model and specialized vocabulary."
```
✅ VERIFIED — `/documentation/speech/sfspeechlanguagemodel`.

The call, as Apple's 2026 article makes it:

```swift
try await SFSpeechLanguageModel.prepareCustomLanguageModel(for: trainingData, configuration: lmConfiguration)
```
✅ VERIFIED — verbatim from *"Recognizing speech in live audio"*, §"Prepare to record and transcribe
speech".

Note the shape: the documented signatures are **completion-handler based**
(`…completion:`), and Apple's 2026 call site uses `try await`. That is Objective-C-style async
bridging doing its job — the `completion:` label vanishes and the method becomes `async throws`.
Both spellings describe the same method. Write the `await` form.

Two things this call is doing: it is **compiling** your training data into whatever runtime form the
dictation engine wants, and it is **caching** the result — which is why the second overload exists
with `ignoresCache:`. This is not instant. Do it once at launch or on first use, not before every
transcription.

> 🔴 **GAP — the type of the `for:` parameter, and the initializer of
> `SFSpeechLanguageModel.Configuration`.** Neither is published on any page we fetched. Apple's call
> site names the argument `trainingData`; `SFCustomLanguageModelData.export(to:)` writes to a file;
> and `Configuration` is described as *"An object describing **the location** of a custom language
> model and specialized vocabulary"* — so a `URL`-shaped story is strongly implied on both sides.
> **What we will not do is invent the initializer.**
>
> **Resolving this** needs `/documentation/speech/sfspeechlanguagemodel/configuration` or an SDK
> interface dump.
>
> **Safe default:** structure your code so the two unknowns are isolated in one small function with
> one call site, then fix it in five minutes against autocompletion on a real machine:
>
> ```swift
> /// 🔴 The two lines inside this function are the ONLY unverified API surface in the
> ///    custom-vocabulary path. Everything else in §11 is documented.
> func prepareCustomLanguageModel(bundledAs name: String) async throws -> SFSpeechLanguageModel.Configuration {
>     guard let url = Bundle.main.url(forResource: name, withExtension: "bin") else {
>         throw DictationError.customModelMissing(name)
>     }
>     let configuration = /* SFSpeechLanguageModel.Configuration(…url…) */
>     try await SFSpeechLanguageModel.prepareCustomLanguageModel(for: url, configuration: configuration)
>     return configuration
> }
> ```

⚠️ **Deprecation note.** The two `clientIdentifier:` overloads are marked *(Deprecated)*. If you are
maintaining iOS 17-era code that uses them, migrate to the two-argument forms — this is a rename, not
a behaviour change, and it is the only deprecation in the custom-vocabulary surface.

### 11.6 Stage 3: attaching it to the transcriber

Covered in §4.4, repeated here because it is the payoff:

```swift
let contentHints = if let lmConfiguration {
    preset.contentHints.union([.customizedLanguage(modelConfiguration: lmConfiguration)])
} else {
    preset.contentHints
}
```
✅ VERIFIED — verbatim from Apple's article.

The wiring across the API-generation boundary is worth naming explicitly, because it is the one
place the iOS 17 types and the iOS 26 types meet:

> ✅ **VERIFIED** — `/documentation/speech/sfspeechlanguagemodel` plus
> `/documentation/speech/dictationtranscriber/contenthint`:
> `DictationTranscriber.ContentHint.customizedLanguage(modelConfiguration:)` takes an
> `SFSpeechLanguageModel.Configuration`.

So the whole nine-year-old `SFSpeechLanguageModel` machinery plugs into the brand-new analyzer stack
through exactly one static function on one struct. That is why §3.4 says custom vocabulary is a
`DictationTranscriber`-only feature: it is not that `SpeechTranscriber` refuses custom models, it is
that there is no hint type on `SpeechTranscriber` for the configuration to travel through.

### 11.7 Failure modes

None of these throw where you would want them to.

| What went wrong | Symptom |
|---|---|
| The `.bin` is not in the bundle | `Bundle.main.url(forResource:)` returns `nil` — **your** guard catches this, nothing in Speech does |
| `prepareCustomLanguageModel` was never called | Transcription works, custom terms are never recognised. No error. |
| The hint was built but never unioned into `contentHints` | Same. No error. |
| The `.bin`'s locale ≠ the transcriber's locale | 🔴 Unverified. Presumably ignored. No error expected. |
| An X-SAMPA symbol is unsupported for the locale | 🔴 Unverified — presumably that pronunciation is dropped. Validate at build time (§11.3). |
| You used `SpeechTranscriber` | Does not compile — no `contentHints:` parameter. **The one loud failure in this table.** |

> ⚠️ **SILENT FAILURE — the custom language model that is never applied.** Four of the six rows
> above produce *working transcription that ignores your vocabulary*. The app looks fine; the
> feature is absent. Because the whole point of a custom language model is a marginal accuracy
> improvement on rare words, its absence is nearly invisible in casual testing — you have to
> specifically speak the jargon and check.
>
> **Test it deliberately:** record yourself saying three of your rarest terms, transcribe with the
> model attached and with `lmConfiguration: nil`, and diff. If the two transcripts are identical,
> your model is not being applied — regardless of what the code looks like.

---

## 12. `SpeechDetector`: gating on voice activity

### 12.1 What it is for

```swift
final class SpeechDetector                 // iOS 26.0+ … tvOS 26.0+, visionOS 26.0+
init()                                     // "Creates a speech detector with default settings."
init(detectionOptions:reportResults:)
struct SpeechDetector.DetectionOptions
SpeechDetector.SensitivityLevel            // has at least .medium
var results
struct SpeechDetector.Result
```
✅ VERIFIED — `/documentation/speech/speechdetector`.

> ✅ **VERIFIED**, same page, verbatim: *"This module asks 'is there speech?' and provides you with
> the ability to **gate transcription by the presence of voices, saving power** otherwise used by
> attempting to transcribe what is likely to be silence."*

It is a **module**, not a filter you wrap around the transcriber. You add it to the same analyzer,
alongside the transcriber, and the analyzer does the gating internally.

```swift
let transcriber = SpeechTranscriber(..)
let speechDetector = SpeechDetector()
let analyzer = SpeechAnalyzer(.., modules: [speechDetector, transcriber])
```
```swift
let analyzer = SpeechAnalyzer(..)
let transcriber = SpeechTranscriber(..)
let speechDetector = SpeechDetector()
try await analyzer.setModules([transcriber, speechDetector])
```
✅ VERIFIED — both snippets reproduced verbatim from Apple's page, `..` placeholders included. Note
the module order differs between them, which suggests order is not significant.

### 12.2 The constraint and the trade

> ✅ **VERIFIED**, same page, verbatim:
>
> ***IMPORTANT** — This module **only functions in conjunction with a `SpeechTranscriber` or
> `DictationTranscriber` module**.*
>
> ***NOTE** — For certain use cases, such as those with a lot of silence, it might be tempting to
> always enable voice activated transcription. But **if the model drops audio that does contain
> speech, there could be a tradeoff** between the power being saved by always having VAD enabled
> and potentially lower accuracy transcriptions. You can set the aggressiveness of the VAD model
> with `SpeechDetector.SensitivityLevel`. **While `.medium` is recommended for most use cases**,
> the value of these tradeoffs will be context-specific.*

The trade is honest and it is not free. A VAD that is too aggressive discards quiet speech — the
end of a sentence where the speaker trails off, a soft-spoken user, a word spoken during a car's
road noise. What you get back is not a *wrong* transcription; it is a **missing** one. And missing
transcription from a VAD looks exactly like missing transcription from the §9 cancellation bug,
which is a good reason not to introduce both at once while you are still debugging.

**Use it** for always-on listening, long recordings with real silence, and battery-sensitive
contexts. **Do not use it** for short dictation where the user is actively speaking the whole time
— there is no silence to save power on, and you have added a failure mode for nothing.

### 12.3 ⚠️ `SpeechDetector.Result` is not what its name suggests

> ⚠️ **SILENT FAILURE — reading `speechDetector.results` expecting speech/silence events.**
>
> ✅ **VERIFIED** — `/documentation/speech/speechdetector`, on `SpeechDetector.Result`, verbatim:
> *"Please note, these must be enabled via [`reportResults`] and currently only support **error
> handling from the VAD model**."*
>
> The `results` stream is for **VAD model errors**, not for a stream of "speech started" /
> "speech ended" booleans. Code written on the assumption that iterating `speechDetector.results`
> yields voice-activity events will compile, run, and produce nothing — a loop that never fires,
> which reads as "there is no speech in this audio" rather than "I am reading the wrong stream."

If you need voice-activity *events* for UI — a level meter, a "listening" indicator, an
auto-stop-after-silence behaviour — `SpeechDetector` is not the API. Use the transcriber's own
result cadence (results stop arriving during silence) or `analyzer.volatileRange` (§2.4), or read
levels off the capture session directly.

> 🔴 **GAP — `SpeechDetector.DetectionOptions` members, `SensitivityLevel`'s full case list, and
> the type of `reportResults:`.** Only `.medium` is attested for `SensitivityLevel`; `.low` and
> `.high` are the obvious companions and are **not** confirmed. `reportResults:` is presumably a
> `Bool` given the wording "these must be enabled via reportResults". The
> `/documentation/speech/speechdetector/detectionoptions` and `/sensitivitylevel` pages were not
> fetched. **Safe default:** use `SpeechDetector()` — the no-argument initializer is documented as
> "default settings", and `.medium` is Apple's own recommendation for most cases, so the default is
> very likely already what you want.

---

## 13. Resource limits, model retention, prewarming

### 13.1 ⚠️ There is a cap on simultaneous analyzers

This is the footgun that only shows up under load, which means it shows up in production.

> ✅ **VERIFIED** — `/documentation/speech/speechanalyzer/options`, verbatim:
>
> *The system normally limits simultaneous analyses to a conservative number, considering hardware
> capabilities of different devices. If you exceed that number, the system throws an
> **`insufficientResources`** error (`SFSpeechError.Code.insufficientResources`).*
>
> *To override the normal limits, create an analyzer with a `SpeechAnalyzer.Options` object with its
> `ignoresResourceLimits` value set to `true`. **The system allows an unlimited number of analyzers
> configured with this option. However, the hardware requirements of numerous analyzers will
> eventually exceed the system's actual capacity, and one or more of the analyzers will fail,
> throwing an unpredictable error.***
>
> ***WARNING** — When using this option, test your app on a variety of devices under a variety of
> scenarios to experimentally determine how many analyzers you can reliably create and expect to
> function. Consider how to recover in the event one or more analyzers fail.*

Read that middle paragraph carefully. `ignoresResourceLimits: true` does not raise the limit; it
**removes the error that tells you about the limit**. You still hit the hardware ceiling, you just
hit it as "an unpredictable error" instead of a named, catchable one.

> ⚠️ **SILENT FAILURE, of the worst kind: trading a good error for a bad one.**
> `SFSpeechError.Code.insufficientResources` is a specific, documented, actionable failure — you
> catch it, you queue the work, you tell the user. Setting `ignoresResourceLimits: true` to "fix"
> it converts a clean back-pressure signal into a nondeterministic failure at a different, unknown
> threshold, on a different device than the one you tested on. **Do not set it because you saw
> `insufficientResources` in the console.** Set it only if you have measured a device-by-device
> ceiling and built recovery, exactly as Apple's warning says.

The correct response to `insufficientResources` is a **queue**: one analyzer at a time, or N where
N is small and configurable. Remember §2.1 — one analyzer can hold multiple modules, and multiple
transcribers *"can share the same backing engine instances and models, so long as the transcribers
are configured similarly in certain respects"* (✅ VERIFIED,
`/documentation/speech/speechtranscriber`). If you think you need eight analyzers, check first
whether you need one analyzer with eight modules.

Also recall from §2.1: *"The analyzer can only analyze one input sequence at a time."* So
"transcribe four files in parallel" genuinely does mean four analyzers, and genuinely is the case
this limit exists to constrain.

### 13.2 Model retention

```swift
struct SpeechAnalyzer.Options              // Equatable, Sendable
init(priority:modelRetention:)
init(priority:modelRetention:ignoresResourceLimits:)
var priority                               // "The priority of analysis processing work."
var modelRetention: Options.ModelRetention
var ignoresResourceLimits: Bool

enum SpeechAnalyzer.Options.ModelRetention // CaseIterable, Equatable, Hashable, Sendable
case lingering        // "Keeps the models in memory for a time so that they can be reused by
                      //  another compatible analyzer session."
case processLifetime  // "Keeps the models in memory until this process exits."
case whileInUse       // "Releases the models when the analyzer is deallocated."
```
✅ VERIFIED — `/documentation/speech/speechanalyzer/options`,
`/documentation/speech/speechanalyzer/options/modelretention-swift.enum`.

| Retention | Use when |
|---|---|
| `.whileInUse` | One-shot transcription. Memory back immediately. |
| `.lingering` | The user dictates repeatedly — a notes app, a chat composer. Second session starts fast without holding memory forever. |
| `.processLifetime` | Transcription *is* your app. A dedicated dictation or captioning app. |

🔴 **GAP — which retention is the default, and the type of `priority:`.** Neither is published.
`priority` is described as "The priority of analysis processing work", which suggests `TaskPriority`,
but we will not guess it into a code listing. **Safe default:** use `SpeechAnalyzer(modules:)`
without options, which is what both Apple's canonical example and its 2026 article do. Reach for
`Options` only when you have a measured reason.

### 13.3 Lazy loading and prewarming

> ✅ **VERIFIED** — `/documentation/speech/speechanalyzer/options`, verbatim: *"By default, the
> analyzer and modules **load the system resources that they require lazily**, and unload those
> resources when they're deallocated. To proactively load system resources and 'preheat' the
> analyzer, call `prepareToAnalyze(in:)` after setting its modules."*

The user-visible consequence: the **first** result after tapping record is late, because the models
are loading while the user is already talking. With `progressiveLongDictation` that shows up as a
second or two of nothing followed by a burst of text.

The fix is one call at the right moment — when the compose field gains focus, when the record screen
appears, when the user starts holding the button:

```swift
// 🟡 Ours. `prepareToAnalyze(in:)` is ✅ VERIFIED as a member; its parameter type is not
//    published, so this is written as a shape rather than a compiling call.
//    Apple's own phrasing: "call prepareToAnalyze(in:) after setting its modules."
//
// 🔴 GAP: the `in:` parameter. The two-argument overload is
//    `prepareToAnalyze(in:withProgressReadyHandler:)`, which suggests `in:` is a format or
//    a context rather than a duration. Verify at the call site.
func preheat(analyzer: SpeechAnalyzer) async throws {
    // try await analyzer.prepareToAnalyze(in: <format-or-context>)
}
```

Pair it with `.lingering` retention and a repeat-dictation flow gets noticeably snappier for one
line of code and a bounded memory cost.

---

## 14. The other path: `CoreAISpeech` and Whisper on Core AI

`SpeechAnalyzer` is not the only way to get speech-to-text on an Apple device in 2026. The
`apple/coreai-models` repository — the same package that provides `CoreAILanguageModel` for
Foundation Models (see [Part 4](../../part-04-beyond-the-built-in-model/)) — ships a **`CoreAISpeech`**
Swift product that runs **your own ASR model** on the Core AI runtime.

These are not competing implementations of the same thing. They are different products with
different trade-offs, and the choice is usually easy once you see them side by side.

### 14.1 What `CoreAISpeech` is

Four files, 528 lines, and the honest assessment first:

> ✅ **VERIFIED** — read from the `apple/coreai-models` source tree: `CoreAISpeech` is **the least
> polished of the package's four non-LLM products**. No `ModelBundle`, no `PreparedModel`, no test
> target (`SegmentationTests`, `ObjectDetectorTests` and `CoreAISharedTests` exist; **there is no
> `SpeechTests`**), hardcoded tensor names, and a hardcoded fallback tensor shape.

```swift
public actor SpeechModel {
    public init(resourcesAt url: URL,
                decoder: any SpeechDecoder = WhisperDecoder(),
                melConfig: MelConfig = .whisper) async throws   // calls warmUp() in init
    public func transcribe(audioURL: URL) async throws -> String
    public func transcribe(pcm: [Float]) async throws -> String // 16 kHz mono
}

public protocol SpeechDecoder: Sendable {
    func decode(encoderOutput: NDArray, encoderOutputShape: [Int],
                decoderModel: AIModel, config: GenerationConfig) async throws -> [Int32]
}
public struct WhisperDecoder: SpeechDecoder { /* greedy */ }

public struct SpeechBundle: Sendable {
    public let encoder: AIModel
    public let decoder: AIModel
    public let tokenizer: (any Tokenizer)?
    public let generationConfig: GenerationConfig
    public init(at url: URL) async throws
}
```
✅ VERIFIED — `swift/Sources/CoreAISpeech/SpeechModel.swift:17-130`, `SpeechDecoder.swift:13-97`,
`SpeechBundle.swift:22-125`.

The bundle layout is a **convention hardcoded in an initializer**, not a manifest:

```
<bundle-dir>/
  encoder.aimodel           REQUIRED — audio features → encoder hidden states
  decoder.aimodel           REQUIRED — autoregressive decoder with persistent KV state
  generation_config.json    optional — falls back to GenerationConfig.whisper
  tokenizer.json            optional — else falls back to the HF cache
```
✅ VERIFIED — `SpeechBundle.swift:28-46`.

### 14.2 The gap that matters most

> ⚠️ **Nothing in `apple/coreai-models` produces the encoder/decoder split that `SpeechBundle`
> requires.**
>
> ✅ VERIFIED: the package's `BundleKind` enum is `{llm, vlm, diffusion, segmenter}` — **there is
> no `.speech` case and no `.detector` case** — yet `SpeechBundle.init(at:)` demands both an
> `encoder.aimodel` and a `decoder.aimodel`, throwing
> `SpeechError.missingModel("bundle at … must contain encoder.aimodel and decoder.aimodel")` if
> either is absent. **The export tooling in the repository does not emit that pair.**

So adopting `CoreAISpeech` means producing the two-model split yourself, from PyTorch, through the
Core AI conversion path — which is [Part 8](../../part-08-coreai-pytorch-conversion/) territory and
is a substantially larger project than "add a Swift package". The split itself is not incidental,
either: per [Part 7](../../part-07-coreai-swift-runtime/), splitting a model into multiple
entrypoints is what routes it to the Neural Engine, so the encoder/decoder division is a
performance requirement as much as an architectural one.

### 14.3 Other sharp edges worth knowing before you commit

All ✅ VERIFIED from source:

- **Only the first 30 seconds of audio is transcribed.** `MelSpectrogram.fromPCM` truncates or
  zero-pads to exactly `nFrames * hopLength` samples — 3000 × 160 = 480,000 samples at 16 kHz
  (`MelSpectrogram.swift:42-46`). **There is no chunking or windowing anywhere in the product.**
  Long-form transcription is entirely your problem.
- **`maxDecodeSteps` defaults to 50 tokens** (`SpeechBundle.swift:86-91`) — roughly one sentence.
- **The tokenizer fallback reaches outside the bundle**, into
  `~/.cache/huggingface/hub/models--openai--whisper-large-v3-turbo/snapshots/<first>`
  (`SpeechBundle.swift:48-69`). That works on a developer Mac and fails on a device. The error
  message admits it: *"Tokenizer not found — ensure the model bundle includes a tokenizer or the HF
  cache is populated"*. **Ship `tokenizer.json` inside the bundle.**
- **`encOutShape ?? [1, 1500, 1280]`** (`SpeechModel.swift:117`) is a hardcoded
  Whisper-large-v3-turbo fallback shape, and `bundle.encoder.functionDescriptor(for: "main")!` is
  force-unwrapped in three places (`:65`, `:88`, `:106`).
- **The mel spectrogram is a hand-rolled DFT by dense matrix multiply, not an FFT** — two
  `cblas_sgemv` calls per frame over a `[201 × 400]` basis, 3000 frames. That is O(nFFT²) per frame
  where O(nFFT log nFFT) was available. It is correct (a faithful librosa/Whisper reimplementation
  down to the `(max(x, maxVal - 8) + 4) / 4` normalisation) and it is the obvious thing to replace
  with `vDSP_DFT` if you adopt this.
- **`MelConfig.whisper`** is `sampleRate: 16_000, nFFT: 400, hopLength: 160, nMelBins: 128,
  nFrames: 3_000` — 25 ms window, 10 ms hop (`MelSpectrogram.swift:24-25`).

There is a CLI, `speech-runner`, with **positional arguments and no options at all**:

```bash
swift run -c release speech-runner ~/models/whisper-turbo ./audio.wav
swift run -c release speech-runner ~/models/whisper-turbo         # 30s-silence latency benchmark
```
✅ VERIFIED — `SpeechRunnerMain.swift:18-26`. Omitting the audio path feeds 480,000 zero samples and
reports total milliseconds. That is the only benchmark facility in the product.

> ⚠️ **No performance number is published for `CoreAISpeech`, or for any non-LLM model in
> `apple/coreai-models`.** The repository's `Tools/benchmark` target is actually `llm-benchmark` and
> imports `CoreAILanguageModels`; **there is no non-LLM benchmark tool**, and no quality or latency
> figure appears anywhere in the repo for speech, segmentation, detection or diffusion. Anyone
> quoting you a "Core AI Whisper is N× faster" number is not quoting Apple. Measure it yourself with
> `speech-runner`'s silence benchmark, on your hardware, and report it as your own measurement.

### 14.4 Choosing between them

| | **SpeechAnalyzer** | **CoreAISpeech** |
|---|---|---|
| Model | Apple's, downloaded and managed by the system | Yours, converted and shipped by you |
| Model size in your app | **Zero** — assets are system-managed and shared between apps | The full weights, in your bundle or downloaded by you |
| Languages | `supportedLocales`, system-maintained | Whatever your model supports |
| Live / streaming | ✅ First-class — volatile results, time ranges, VAD | ❌ Batch only; 30-second ceiling; no streaming path |
| Long audio | ✅ `longDictation` presets exist for it | ❌ You write chunking yourself |
| Custom vocabulary | ✅ `SFCustomLanguageModelData` (§11) | Whatever your model and decoder support |
| Custom decoding (beam search, constrained decoding) | ❌ Closed | ✅ `SpeechDecoder` is a protocol you implement |
| Model choice / pinning | ❌ System model, updated by Apple | ✅ Exactly the weights you shipped |
| Runs offline first-launch | ❌ Needs an asset download (once, shared) | ✅ Weights are already there |
| Maturity | Shipping framework, two OS generations | Least polished product in its package; no tests |
| Effort to adopt | Hours | Weeks, and it starts in PyTorch |

**The decision rule.** If you want *transcription*, use `SpeechAnalyzer` — it is better at it, it is
free, it streams, and it has custom vocabulary. Choose `CoreAISpeech` only when you need something
`SpeechAnalyzer` structurally cannot give you: **a specific model you must pin**, **a language Apple
does not support**, **custom decoding**, or **zero dependence on system asset downloads** (an app
that must work on a device that has never been online).

Those are real requirements and they do occur. They are just much rarer than "I want speech-to-text",
and the cost difference between the two columns is roughly two orders of magnitude of engineering
time.

**Cross-references:** the Core AI runtime, `AIModel`, `InferenceFunction` and persistent state are
[Part 7](../../part-07-coreai-swift-runtime/); converting a Whisper checkpoint to `.aimodel` is
[Part 8](../../part-08-coreai-pytorch-conversion/); `CoreAISpeech`'s decoder is also the repository's
clearest worked example of `InferenceFunction` KV-cache state, which Part 7 uses as its case study.

---

## 15. Declared gaps

Every unresolved item in this guide, in one place, with what would close it. None of these is
guessed at anywhere in the text above; each one has a stated safe default.

| # | Gap | Why it is open | What resolves it | Safe default |
|---|---|---|---|---|
| **G1** | **`progressiveLongDictation` vs `.audioTimeRange`.** Apple's article merges by time range using a preset the preset page says has no time-range attributes (§8.3). | Two Apple pages disagree; the sample that would settle it is unavailable (§1.2). | Print `result.text.runs` for a volatile result on an iOS 27 device; or read the SpokenWord source. | `.union([.audioTimeRange])` explicitly. Costs nothing, removes the ambiguity. |
| **G2** | `AssetInventory.Status` is `Comparable`, ordering unpublished. | Ordering not stated on the page. | `print([Status.installed, .downloading, .supported, .unsupported].sorted())` on macOS 27. | `switch` on all four cases. |
| **G3** | `AnalyzerInputConverter(analyzerFormat:)` appears to accept an `AVAudioFormat?` in Apple's own example. | Apple's canonical snippet passes an unwrapped optional. | SDK interface dump. | Unwrap it yourself before calling. You need a non-nil format anyway (§5.5). |
| **G4** | Type of `CaptureInputSequenceProvider.captureAudioDataOutput`; whether `priority:` is defaulted. | Members are documented by description only. | Option-click in Xcode 27. | Use the two-argument `providerWithSession(from:compatibleWith:)`; bind the output with `let` and let inference work. |
| **G5** | Value of `AssetInventory.maximumReservedLocales`. | Not published; likely device-dependent. | One `print` on a device. | Assume 1. Release aggressively. Treat the throw as recoverable. |
| **G6** | **Provenance of `withTaskCancellationShield`.** | Appears in Apple's article and nowhere else in the corpus. | Type the name in a scratch file with the Xcode 27 toolchain. | Write your own (§9.4) — the semantics are unambiguous, and an unstructured `Task` already has them. |
| **G7** | Element/failure types of `provider.analyzerInputs`. | Documented as "an asynchronous sequence" with no declaration. | SDK interface dump. | Do not annotate; pass it straight to `analyzeSequence(_:)`. |
| **G8** | `AnalyzerInputConverter.convert(_:at:)` — the type and meaning of `at:`. | Apple's example passes `nil`; no declaration published. | SDK interface dump. | Pass `nil` for contiguous audio. |
| **G9** | Argument type of `AssetInputSequenceProvider.provider(from:)` — `AVAsset` vs `URL`. | Description says "an asset **or file**". | Try both; one compiles. | `AVURLAsset(url:)`. |
| **G10** | `DictationTranscriber` option-enum full case lists. | Individual enum pages not fetched. | Fetch `/dictationtranscriber/transcriptionoption`, `/reportingoption`, `/resultattributeoption`. | Start from a preset; union only the attested cases (§4.3). No exhaustive `switch`. |
| **G11** | `DictationTranscriber.Result` members — does it have `alternatives`? | Page not fetched. | Fetch `/documentation/speech/dictationtranscriber/result`. | Use only `text`, `range`, `isFinal`. |
| **G12** | Reading a confidence value from an `AttributedString` run. | Speech attribute-scope property names not harvested. | Fetch `/documentation/foundation/attributescopes/speechattributes`. | Iterate `runs` and inspect the attribute container; do not hardcode a key path. |
| **G13** | `SFSpeechLanguageModel.Configuration`'s initializer, and the type of `prepareCustomLanguageModel(for:)`. | Neither published. **This is the only unverified API in the entire custom-vocabulary path.** | Fetch `/documentation/speech/sfspeechlanguagemodel/configuration`. | Isolate both in one small function (§11.5) and fix against autocompletion in five minutes. |
| **G14** | Whether mixing `PhraseCount`, `PhraseCountsFromTemplates` and `CustomPronunciation` in one result-builder block is legal. | Two distinct builder protocols (`DataInsertable` / `TemplateInsertable`). | Compile it. | Fall back to the imperative `insert(...)` form — all four methods are documented. |
| **G15** | Whether a `Template`'s `count:` is per-expansion or divided across expansions. | Not documented. | An A/B recognition experiment. | Treat counts as relative weights on one consistent scale; tune empirically. |
| **G16** | Return type of `SFCustomLanguageModelData.supportedPhonemes(locale:)`; whether it is `async`. | Described only in prose. | Compile it — this runs in *your* build-time CLI. | `let allowed = try await …` and let inference decide. |
| **G17** | `SpeechDetector.DetectionOptions` members; `SensitivityLevel`'s full case list; type of `reportResults:`. | Pages not fetched. Only `.medium` attested. | Fetch `/speechdetector/detectionoptions`, `/sensitivitylevel`. | `SpeechDetector()` — documented as "default settings", and `.medium` is Apple's recommendation. |
| **G18** | `SpeechAnalyzer.Options.priority`'s type; the default `ModelRetention`. | Not published. | SDK interface dump. | `SpeechAnalyzer(modules:)` with no options, as both Apple examples do. |
| **G19** | `prepareToAnalyze(in:)`'s parameter. | Not published. The `(in:withProgressReadyHandler:)` overload hints it is a format or context, not a duration. | SDK interface dump. | Skip prewarming until you have measured that first-result latency is a real problem. |
| **G20** | Which `finish`/`finalize` methods are `async`. | Index page lists names without declarations; the canonical example shows both forms. | Compile. | Write `try await`; delete the `await` if the compiler objects. |
| **G21** | Whether the modern stack needs speech-recognition authorization. | Apple's 2026 article requests **only** `AVCaptureDevice.requestAccess(for: .audio)`. The legacy `asking-permission-to-use-speech-recognition` article still exists. | Run on a device with speech recognition denied. | Request microphone access as Apple's article does. If you also support the legacy `SFSpeechRecognizer` path, request both. |
| **G22** | The Info.plist usage-description key AVFoundation requires for microphone capture. | Not covered by any source read for this guide. | AVFoundation's capture-authorization documentation. | Consult AVFoundation's docs before shipping — a missing key is an immediate launch-time crash on device, so this one at least fails loudly. |
| **G23** | Native macOS availability of the SpokenWord sample (§"What you need"). | The article's availability line omits macOS, though `CaptureInputSequenceProvider` lists macOS 27. | Fetch the sample project. | Treat the API as macOS 27 (its own page says so); expect to write macOS capture plumbing yourself. |
| **G24** | Whether a `.bin`'s locale mismatching the transcriber's locale is ignored or errors (§11.7). | Not documented. | Test on device. | Ship one `.bin` per locale, named with the locale as Apple's sample does. |
| **G25** | Whether bumping `SFCustomLanguageModelData.version` invalidates the on-device prepared-model cache. | The existence of an `ignoresCache:` overload implies caching is keyed on *something*, unspecified. | Test: prepare, change data, bump version, prepare again, check recognition. | Bump `version` on every data change. If that is insufficient, the `ignoresCache:` overload exists. |

**Two of these are worth resolving before you write much code**: **G1** (because it silently
corrupts your transcript) and **G13** (because it is the only genuinely unverified API call in the
custom-vocabulary path). Both take under ten minutes on a real machine.

### 15.1 Where each claim in this guide comes from

For auditability, since a previous batch in this series was found to contain a fabricated listing:

| Class | Count in this guide | Examples |
|---|---|---|
| Verbatim quotes from Apple's 2026 article | ~14 code fragments + ~10 prose blocks | The transcriber constructor, the capture-provider call, the two-line analysis core, the merge branch, the cancellation-shield task group, all four DSL fragments |
| Verbatim quotes from Apple reference pages | ~30 declarations + ~25 prose blocks | The whole `SpeechAnalyzer` surface, both preset matrices, `AssetInventory`, `AnalyzerInput`, `SpeechDetector`, `SFCustomLanguageModelData` |
| Quotes from a compiling Apple sample (iOS 26, stale) | 3 blocks | Locale comparison by BCP-47, the asset ladder, the two-transcript merge |
| Quotes from an Apple staff forum reply | 1 | Thread 834149, "no new API has been released specific to that model" |
| Read from `apple/coreai-models` source | §14 entirely | Line-numbered citations throughout |
| **Assembled by us and marked 🟡** | ~8 listings | `makeTranscriber` composition, `switchLocale`, `transcribeFile`, `makeInputSequence`, `withTaskCancellationShield`, the `datagenerator` CLI, `TranscriptStore`, the §10 controller |
| **Declared 🔴 unknown** | 25 | The table above |

Nothing in this guide is written from recollection of an API. Where a name, type or default could
not be traced to a source read this session, it appears in the gap table rather than in a code
listing.

---

## 16. Silent-failure checklist

The defining property of this stack is that **most defects do not throw**. Here is every one this
guide identified, in the order you are likely to hit them.

| # | Failure | Symptom | Fix |
|---|---|---|---|
| 1 | **`bestAvailableAudioFormat` before installing assets** (§5.5) | Returns `nil`. If you `??` a default, the analyzer gets audio in a format its modules never agreed to — and it does no conversion. Empty or garbage transcript, clean console. | Assets first, format second. Always. |
| 2 | **Force-unwrapping `assetInstallationRequest(supporting:)`** (§5.3) | Crashes on devices where the assets are already installed — i.e. the happy path. Works on your fresh test device. | `if let`. |
| 3 | **Terminating the input sequence to "stop"** (§2.3) | Result streams never terminate. `for try await` hangs forever. Task group never returns. Stop button appears to freeze. | Call a `finish` method, or use `finalizeAndFinishThroughEndOfInput()`. |
| 4 | **No cancellation shield on the display task** (§9) | **The last phrase of every recording is silently lost.** Does not reproduce when you pause before hitting stop — which is how everyone tests. | Shield the display task; let the analysis task be cancellable. |
| 5 | **`rangeOfAudioTimeRangeAttributes` with a preset that has no `.audioTimeRange`** (§8.3) | Always returns `nil` → always appends → transcript reads *"I went to the I went to the store I went to the store today."* | `.union([.audioTimeRange])`, or use a `timeIndexed…` preset. |
| 6 | **Never calling `AnalyzerInputConverter.flush()`** (§6.6) | The tail of every recording dies inside the converter, before the analyzer sees it. A *second*, independent way to lose the last words. | Always flush after the last buffer. |
| 7 | **Comparing `Locale` values directly instead of `.identifier(.bcp47)`** (§3.3) | `supportedLocales.contains(Locale.current)` is `false` for a fully supported language, because `Locale.current` carries calendar and measurement preferences. You conclude the language is unsupported. | `supportedLocale(equivalentTo:)`, or compare BCP-47 identifiers. |
| 8 | **Reading `speechDetector.results` for voice-activity events** (§12.3) | The stream carries VAD **errors**, not speech/silence events. Your loop never fires, which reads as "there is no speech". | Do not use `SpeechDetector.Result` for events. Use transcriber cadence or `volatileRange`. |
| 9 | **`ignoresResourceLimits: true` to silence `insufficientResources`** (§13.1) | Replaces a clean, catchable, documented back-pressure signal with "an unpredictable error" at an unknown, device-dependent threshold. | Queue your analyzers. Or fold multiple modules into one analyzer. |
| 10 | **A custom language model that is never applied** (§11.7) | Transcription works; your vocabulary is simply ignored. Four separate mistakes produce this identical outcome, all silent. | A/B test: transcribe your rarest terms with and without the configuration, and diff. |
| 11 | **First result arrives seconds late** (§13.3) | Not a bug — lazy model loading. But it looks like one, and users start talking into a void. | `prepareToAnalyze(in:)` when the UI appears; `.lingering` retention for repeat use. |
| 12 | **Copy-pasting Apple's `Preset` snippets** (§4.3) | They are missing the commas between arguments and do not compile. Both preset pages have the same defect. | Add the commas. It is a docs typo, not your misunderstanding. |

### 16.1 The four-line version

If you remember nothing else:

1. **Assets before format, format before analyzer, analyzer before audio.**
2. **Shield the display task from cancellation; let the analysis task be cancelled.**
3. **If you merge by time range, put `.audioTimeRange` in `attributeOptions` yourself.**
4. **Ending the input sequence is not how you stop. Call a `finish` method.**

---

## 17. Sources

Everything cited in this guide, with the evidence class it belongs to.

**Apple documentation — articles** (fetched 2026-07-27 via `sosumi.ai` mirrors of
`developer.apple.com`):

- `/documentation/speech/recognizing-speech-in-live-audio` — **the primary source for this guide.**
  Marked `iOS 27.0+ Beta, iPadOS 27.0+ Beta, Mac Catalyst 27.0+ Beta, Xcode 27.0+ Beta`. Sections
  quoted: "Configure the speech analyzer", "Configure the capture session", "Analyze audio and
  display results", "Stop the capture session", "Prepare to record and transcribe speech",
  "Customize the language model".
- `/documentation/speech/bringing-advanced-speech-to-text-capabilities-to-your-app` — the WWDC25
  sample page. ⚠️ Cited **only** as evidence that it is stale.
- `/documentation/updates/speech` — the complete 2026 Speech changelog (two bullets).

**Apple documentation — reference pages:**

`/speechanalyzer` · `/speechanalyzer/options` · `/speechanalyzer/options/modelretention-swift.enum` ·
`/speechanalyzer/analyzesequence(_:)` · `/speechanalyzer/bestavailableaudioformat(compatiblewith:)` ·
`/speechtranscriber` · `/speechtranscriber/preset` · `/speechtranscriber/transcriptionoption` ·
`/speechtranscriber/reportingoption` · `/speechtranscriber/resultattributeoption` ·
`/speechtranscriber/result` · `/dictationtranscriber` · `/dictationtranscriber/preset` ·
`/dictationtranscriber/contenthint` · `/speechdetector` · `/speechmodule` · `/speechmoduleresult` ·
`/localedependentspeechmodule` · `/speechmodels` · `/analyzerinput` · `/analyzerinputconverter` ·
`/analysiscontext` · `/assetinventory` · `/assetinventory/status` ·
`/assetinventory/assetinstallationrequest(supporting:)` · `/assetinstallationrequest` ·
`/assetinputsequenceprovider` · `/captureinputsequenceprovider` · `/sfcustomlanguagemodeldata` ·
`/sfspeechlanguagemodel` · `/datainsertable` · `/templateinsertable` — all under
`/documentation/speech/`.

Cross-framework: `AttributeScopes.SpeechAttributes.TimeRangeAttribute`,
`AttributeScopes.SpeechAttributes.ConfidenceAttribute`,
`AttributedString.rangeOfAudioTimeRangeAttributes(intersecting:)` (Foundation).

**Apple sample code** — ⚠️ iOS 26 / WWDC25, cited only for the iOS 26 baseline and clearly labelled
as such at every use:

- `BringingAdvancedSpeechToTextCapabilitiesToYourApp.zip` → `SwiftTranscriptionSampleApp`,
  8 Swift files, `IPHONEOS_DEPLOYMENT_TARGET = 26.0`. Quoted:
  `Recording and Transcription/Transcription.swift:39-82` (setup and the two-transcript merge),
  `:108-142` (the asset ladder).

**Apple Developer Forums** (precedence: above WWDC transcripts, below documentation):

- **Thread 834149**, "TTS Advanced Speech Generation: Expressive voices", opened 2026-06-12 by
  `juan.moya`, 1 reply from Apple staff. The definitive statement that no new speech-generation API
  shipped.
- **Thread 832868**, "Speech generation by the new Foundation Model" — cites the WWDC26 keynote at
  30m:20s. **Zero replies.**

**Apple open source:**

- `apple/coreai-models` — `swift/Sources/CoreAISpeech/{SpeechModel,SpeechBundle,SpeechDecoder,MelSpectrogram}.swift`
  and `Tools/SpeechRunnerMain.swift`. All §14 claims are line-cited.

**Not used, and why:**

- **WWDC session transcripts.** There is **no WWDC26 Speech session in our corpus**, and WWDC25
  session 277 describes the iOS 26 API that §1.2 explains has been superseded on the input side.
  This guide is therefore documentation-first throughout, which is a *stronger* position than
  transcript-derived reconstruction — spoken narration is the origin of most of the phantom API
  spellings this series exists to correct.
- **Community benchmarks.** None exist for this API that we could attribute. No performance number
  in this guide is presented as measured, by us or anyone else, and §14.3 says explicitly that
  Apple publishes none for `CoreAISpeech`.

---

## Related guides

- [Part 7 — Core AI: the Swift runtime](../../part-07-coreai-swift-runtime/) — `AIModel`,
  `InferenceFunction`, persistent state. `CoreAISpeech`'s decoder is the clearest worked example of
  KV-cache state in the whole `coreai-models` package.
- [Part 8 — Core AI: converting from PyTorch](../../part-08-coreai-pytorch-conversion/) — what it
  takes to produce the `encoder.aimodel` / `decoder.aimodel` split `SpeechBundle` requires and that
  nothing in the repository currently emits.
- [Part 2 — Foundation Models: the everyday API](../../part-02-foundation-models-everyday-api/) —
  what to do with a transcript once you have one. Remember `String(result.text.characters)`.
- [Part 1 — Orientation and gating](../../part-01-orientation-and-gating/) — the known-bad-claims
  register, and the platform/version gating patterns this guide's §3.1 matrix feeds into.
