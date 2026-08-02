# Follow-up backlog

Open work carried forward from the **2026-08-02 web harvest** and its implementation pass.
Evidence for every item is already on disk under `notes/web/2026-08-02-harvest/` — these are
*writing* tasks, not research tasks, unless marked otherwise.

**Companion files.** Machine-gated evidence lives in
[`NEEDED-FROM-A-MACOS-27-MACHINE.md`](NEEDED-FROM-A-MACOS-27-MACHINE.md); per-beta ritual lives in
[`NEXT-BETA-CHECKLIST.md`](NEXT-BETA-CHECKLIST.md); recurring refreshes in
[`FRESHNESS-RUNBOOK.md`](FRESHNESS-RUNBOOK.md). This file is only for the harvest residue.

---

## 0. What the 2026-08-02 pass already closed

Recorded so nobody re-does it. Detail in
[`web/2026-08-02-harvest/README.md`](web/2026-08-02-harvest/README.md).

| Closed | Where |
|---|---|
| `fm` CLI surface raised from "no attested flags" to 🟠 seven subcommands + four flag spellings + the `schema object` builder grammar | `part-05` ref 02 §2.1–2.4, §2.6, §3, §17.5 |
| `contextSize` 4096-vs-8192 settled by Apple (Group Lab 8121); shared input+output budget documented | `part-17` ref 01 §1.1, `part-03` ref 01 §3.3, `part-01` ref 01 §3.1 |
| Gap **G6** — `withTaskCancellationShield` is SE-0504 (Swift 6.4 stdlib); polyfill renamed to stop it shadowing | `part-16` ref 01 §9.4 |
| `ConstrainedGenerationSession` rollback / jump-forward / bitmask-fill; `--clear-coreai-cache`; upstream drift incl. the `.llmasset` rename | `part-07` refs 04 §7.3.1 and 02 §7.1, `part-10` ref 03 §18.1 |
| Third-party MLX training layer mapped; the three fine-tuning 🔴 converted to documented ecosystem-wide negatives | `part-12` ref 06 §13 |
| Six transcripts installed (328, 253, 297, 375, 310, 258) | `transcripts/` — 23 → 29 files |

---

## 1. Highest value: an entire framework is missing

### 1.1 🚨 Music Understanding has zero corpus coverage

`MusicUnderstanding` returns **0 hits** across `guides/`, `notes/sdk-interfaces/` and (before this
harvest) `transcripts/`. It is a **new on-device ML framework in the 2026 release** — six analysis
dimensions, `MusicUnderstandingSession`, `AsyncSequence` streaming, everything `Codable`, adopted
by Final Cut Pro for beat detection and iPad montage.

Evidence is complete and on disk: full transcript at `transcripts/wwdc2026-253.txt` plus all 18
verbatim code samples in
[`web/2026-08-02-harvest/wwdc2026-253-music-understanding.md`](web/2026-08-02-harvest/wwdc2026-253-music-understanding.md).

**Work:**

1. **`part-01` ref 01** — add it to the 2026 stack map. The map currently claims to enumerate the
   on-device ML surface and does not know this framework exists. *This is the single most
   misleading omission in the series right now.*
2. **New `part-16` reference 06, `06-music-understanding.md`** — the Speech guide
   (`part-16` ref 01) is the structural template: same shape (on-device analyzer, `AsyncSequence`
   input, streaming results, `CMTime`-stamped output).
3. **Four `SILENT-FAILURES.md` rows**, all stated on stage:
   - `AVURLAssetPreferPreciseDurationAndTimingKey` omitted → degraded results, no error;
   - `analyze(for:)` returns `nil` for dimensions you did not request — same struct, silently
     empty fields;
   - `beatsPerMinute` is `nil` below two detected beats;
   - an `AudioProvider` that never yields a terminating `nil` presumably hangs `analyze()`.
4. **Extend `scripts/dump-sdk-interfaces.sh`** to capture `MusicUnderstanding`, so the guide can be
   SDK-verified rather than transcript-verified. Until then everything is 🟡.

**Two defects in Apple's own published samples must be preserved-and-flagged, never copied:** an
unbalanced generic bracket in `KeyResult` (`RangedValue<KeySignature]`), and a task-group variable
mismatch at 12:55 plus a scalar/array contradiction on `LoudnessResult.momentary` between the
batch (11:45) and streaming (12:55) samples. `scripts/verify-snippets.py` fails hard on the first.

🔴 **Open questions this cannot answer:** the `Instrument` enum case list (never shown), the
streaming-`LoudnessResult` shape contradiction, availability annotations (no `@available` appears
anywhere in the session; Apple says "all Apple platforms"), and the *Music Understanding Lab*
sample app, which has not been located or downloaded. Session **254** ("Integrate MusicKit into
your app") is the companion and is also absent.

---

## 2. Transcripts on disk, guides not yet updated

All six new transcripts are installed but only referenced incidentally. Each of these is a
"write the section" task with the evidence already local.

### 2.1 Session 328 → `part-13` ref 01, `part-12` ref 01

`part-13` already cites `repos/ml-explore__mlx-swift-examples/Numerical/*` but has never cited the
session that explains it. Add:

- the **red/black-checkerboard idiom** — MLX has no in-place update, so Gauss-Seidel-shaped
  algorithms fake it with alternating masks. Language-agnostic; belongs in `part-12` ref 01's
  indexing/in-place material too.
- the **`eval`-in-loop rule** — omitting `eval` inside a loop is correct-but-unbounded graph
  growth. A silent-failure candidate.
- the four-front-end framing ("prototype in Python and ship in Swift") for `part-14`.
- ⚠️ Both performance claims ("10x is certainly possible", "I had to slow SOR down by a factor of
  100") are **unmeasured demo statements**. `part-15` ref 02 should cite them as examples of the
  genre it warns about, not as numbers.

### 2.2 Session 297 → `part-16` ref 03 (13 🔴), ref 02 (18 🔴)

Visual Intelligence has **two integration directions** and the corpus documents neither well:
app → VI via Image Search (`IntentValueQuery` + `SemanticContentDescriptor`), and **VI → app via
system stores** (EventKit / Contacts / HealthKit) — a zero-code path that is currently undocumented.

⚠️ **Verify the schema-domain count.** Session 297 uses
`@AppIntent(schema: .visualIntelligence.semanticContentSearch)`. If
`web/app-intents-siri-schemas.md` §3.5 ("Counting the surface") has no `visualIntelligence` domain,
the committed count is wrong.

Behavioural rules worth lifting verbatim: the ~3-line display budget; empty arrays are legitimate
(the system renders the empty state); **the system decides provider ordering**; `OpenIntent.perform`
runs *as the app foregrounds* (silent-failure candidate); and the macOS/iPad pixel buffer can be
**much larger** than iPhone's.

### 2.3 Session 375 → `part-17` ref 01, `part-01` ref 01

**`ImageCreator` is deprecated.** Belongs in the what-changed checklist beside the adapter sunset
and the `GenerationError` deprecation. State the capability consequence plainly: **there is no
headless image-generation API left** — the replacement is sheet-based UI, so programmatic batch
generation is gone.

Two structural facts for `part-04`/`part-01`: all Image Playground generation now runs on **PCC**,
and its quota is **system-managed with no developer-facing usage UI** — the opposite of the
`QuotaUsage` story Part 4 documents for Foundation Models. `ImagePlaygroundStyle.externalProvider`
is a second, independent instance of "Apple frameworks broker third-party models".

Silent-failure candidate: with `.emoji` active the sheet fires `onAdaptiveImageGlyphCreation` and
**not** `onCompletion` — wire only the latter and you get nothing, with no error.

### 2.4 Session 310 → `part-16` ref 02, `part-02` ref 04

⭐ **Model Transcript Inspector** — Shortcuts can now show the raw structured representation of an
App Entity as the model receives it. The corpus currently *reasons* about what the model sees from
`displayRepresentation` and `@Property`; this is a shipped tool that shows the ground truth, with
no code required. Name it in `part-16` ref 02 and `part-02` ref 04, and add it to
`NEXT-BETA-CHECKLIST.md` as something to actually run.

Also: Shortcuts Storage syncs App Entities via iCloud and therefore needs **stable, device-consistent
identifiers** — the same requirement `SyncableEntity` encodes, stated from a second direction.

🔴 **Chase this:** the Use Model action now has "access to new, more capable Apple Intelligence
models **with the ability to go out to the web**". No FM API surface in the corpus offers web
retrieval. Is it Shortcuts-only, or is there a developer-facing equivalent?

### 2.5 Session 258 → `part-10` ref 02 (11 🔴), `part-15` ref 02

⭐ **Instruments "Top Functions" is new in Xcode 27** and the corpus does not mention it. Generic,
so it applies to inference workloads. Also new: comparing performance runs across recordings.

Organizer additions relevant to shipping: a **Storage metric** that breaks out **binary size**
("binary size impacts cellular downloads and launch time" — directly relevant to bundling models,
`part-15` ref 01), an expanded **hitches** metric, **Metric Goals** calibrated against similar apps
*and* your own history, and **Generate Recommendations**.

> Correction on record: this file's first draft said 258 had no Instruments content. That came from
> a truncated fetch and was wrong. What remains true is narrower — **258 does not close the
> Instruments *lane-names* gap** (`NEEDED-FROM-A-MACOS-27-MACHINE.md` item 3). No Core AI Debugger,
> no FM/Core AI lane names. Do not re-fetch 258 hoping for them.

---

## 3. Findings not yet written into guides

### 3.1 `AnalyzerInput.buffer` is deprecated in 27, and the Speech guide does not say so

From the repo's **own** SDK captures, not the web —
`diff notes/sdk-interfaces/Speech-{26.5,27.0}-macos.swiftinterface`:

```swift
@available(anyAppleOS, deprecated: 27, message: "use other AnalyzerInput properties to get information about audio")
public var buffer: AVFAudio::AVAudioPCMBuffer { … }
```

with three iOS-27-only, **watchOS-unavailable** replacements (`init(buffer: CMReadySampleBuffer<…>)`,
`bufferDuration`, `bufferFormat`). The three new symbols are documented; **the deprecation of what
they replace is not**, and neither is the watchOS unavailability — which is the sharp edge, because
the migration is not uniformly available across platforms. Belongs in `part-16` ref 01 **and**
`part-17` ref 01.

> 🔧 **Tooling idea, cheap and probably productive:** there is no routine that diffs the committed
> 26.5 baseline against the committed 27.0 capture looking for `deprecated:` annotations.
> `grep -rn "deprecated: 27" notes/sdk-interfaces/` would likely surface more of these in one pass.
> `scripts/diff-interfaces.sh` only diffs a *fresh* capture against git.

### 3.2 Group Lab 8121 material still unwritten

Beyond the context-window answer already folded in:

- **Core ML → Core AI repositioning**, in Apple's words: Core ML "is now focused on traditional ML
  like decision trees"; "**anything new involving neural networks should move to Core AI**"; Core AI
  "comes with SLAs and guarantees"; MLX is "the place for on-device training and distributed
  workloads across multiple machines". Decision rule: "**choose the highest level that meets your
  need**." → `part-01` ref 01 and `part-17` ref 05 (15 🔴), which currently infer this from API
  surfaces.
- **The guardrails mechanism** that explains four existing `SILENT-FAILURES.md` rows. Apple
  distinguishes a **refusal** (the model's own aligned response, "seen with guided generation")
  from a **guardrail error** (a separate moderation model inspecting input *and* output). That is
  the missing *why* behind "`permissiveContentTransformations` silently does nothing under
  `@Generable`". → `part-02` ref 06 §5.2, `part-17` ref 03 §10.3. Also new: a **soft refusal in
  natural language that is not an error** and therefore invisible to `catch` — its own row.
- **Background inference is rate-limited.** FM calls work in `BGAppRefreshTask`/`BGProcessingTask`,
  but "if the OS is busy it may rate-limit you — catch the rate-limited error and retry later".
  Cross-check the exact case against the captured 9-case `LanguageModelError` list before naming
  it. → `part-15`, `part-02` ref 06. Strong silent-failure candidate: works in testing, throttles
  in the field.
- **Models are not shared across apps** (stated reason: resource contention), though the system
  caches the frameworks Apple ships. → `part-15` ref 01.
- The Apple Intelligence **waitlist applies only to Siri** — not to PCC, not to on-device.
  → `part-01` ref 02.

### 3.3 M5 prefill/decode asymmetry — first-party, unused

`machinelearning.apple.com/research/exploring-llms-mlx-m5` is **not in the corpus URL inventory**.
It is the cleanest first-party statement of the asymmetry: **TTFT 3.33×–4.06× faster on M5**,
generation only **1.19×–1.27×**, explicitly because decode is memory-bandwidth-bound. Protocol:
4096-token prompt, 128 generated, M5 MacBook Pro 24 GB vs M4. Gate: **macOS 26.2+** for the Neural
Accelerators. → `part-15` ref 02 and `part-12` ref 02. It is also the correct rebuttal to any
"M5 is 4× faster" summary.

### 3.4 `coreai-models` drift not yet re-read

The clone was fast-forwarded `5ed9981` → `49becc6`. Three commits are folded in; **one is not**:

🔴 **`367ad52` "New custom op for KV cache update" (2026-07-29)** rewrote `export/mlir_ops.py`
(+337 lines) and both `primitives/{ios,macos}/cache.py`. Those are the exact files behind
`part-10` ref 03 §627/§939/§2011 and `part-07` ref 03's cache-shape and `seq_len_dim()` claims.
**It may invalidate them.** This is the highest-value re-read in the backlog.

Also unfolded: `c7421ba` (flux2 text-encoder float cast before quantization — check against
`part-09`).

### 3.5 Other clones are stale

`git -C repos/<r> log HEAD..origin/HEAD` before trusting a line number:
`mlx` (2026-07-24), `mlx-lm` (2026-07-26), `coreai-torch` (2026-07-23),
`coreai-optimization` (2026-07-24), `python-apple-fm-sdk` (2026-07-07),
`mlx-swift-examples` (2026-06-15).

---

## 4. Research still open

### 4.1 The session inventory was built from the wrong index

**Root cause of six missed sessions.** The corpus's session list came from
`developer.apple.com/wwdc26/guides/machine-learning/`, which lists **only the 18 ML-track sessions
and no Group Labs**. Sessions carrying ML content in the Siri, Media and Tools tracks were
structurally invisible — the same blind spot that previously hid Tech Talk 111432.

🔧 **Fix `FRESHNESS-RUNBOOK.md`:** the ML-track guide page is not a sufficient inventory. Use
`developer.apple.com/videos/wwdc2026/` or a third-party index.

🔴 **Unswept: 14 of 16 group labs.** `ivan-magda/wwdc26-notes` lists
`8001-8007, 8009-8011, 8013-8015, 8018, 8120-8121`. Only **8121** (ML & AI — high yield) and
**8120** (SwiftUI — not relevant) have been checked. Group labs publish **no caption track**, only
Apple's written Q&A summaries — cite as Apple's paraphrase, never as an engineer's words.

Two full-corpus mirrors found for future sweeps: `pixelfolio/WWDC26-Transcripts` (115 of 134
sessions as Markdown, from Apple's caption tracks) and `ivan-magda/wwdc26-notes` (100+ sessions
with digests, transcripts, code, and an `llms.txt`).

### 4.2 Measurable here, cheaper than searching

- **`--grad-checkpoint` overhead** (`part-12` ref 06 `:1820`). Nobody in the ecosystem publishes a
  memory-saved / time-cost figure. The A/B is ~2 minutes: 50 steps with and without, reading
  `peak_memory` and `iterations_per_second`. **Better closed by running it than by citing anyone.**
  Candidate for a committed benchmark.
- **Swift version in the Xcode 27 beta** — `xcrun swift --version`, to confirm ≥ 6.4 so that
  `withTaskCancellationShield` (SE-0504) actually resolves. One line; the last residue of gap G6.

### 4.3 Negative results — do not re-search these

| Question | Outcome |
|---|---|
| What changed in **Speech** for iOS 27? | The community has written **nothing**. Every result is WWDC25/iOS 26. The SDK diff (§3.1) is the only source. |
| `maximumReservedLocales` **value** | It is a computed property; the value is not in the interface. Runtime probe only. `part-16` ref 01 `:1243` stands. |
| Does system **generated-subtitles** (session 256) expose a Speech API? | **No.** System-level, automatic, `MediaAccessibility` styling only. |
| LoRA-vs-DoRA-vs-full **quality** ablation | Does not exist in `mlx-lm`, `mlx-lm-lora`, `mlx-tune`, `MLX-GRPO`, `SiLLM`, or the ~140-project `awesome-mlx` index. |
| Instruments 27 **lane names** / Core AI Debugger in session 258 | Not there. See §2.5. |

### 4.4 One source to distrust

`chatforest.com/builders-log/apple-fm-cli-python-sdk-fm-serve-openai-compatible-psotu-wwdc-2026/`
retracts its own earlier `fm serve` claim and then argues the subcommand does not exist **from its
absence in a transcript** — the inference this project's house style forbids, contradicted by a
`--help` paste from a named build. 🔧 Add it to `web/community-blogs.md` §9 (unreliable sources)
with that reasoning attached.

---

## 5. Method notes for the next editor

**Editing a guide shifts every callout below the edit**, and `notes/synthesis/callout-classifications/*.tsv`
are keyed on `(file, line, kind)`. `scripts/build-indexes.sh` refuses to build until they are
re-keyed. Match on `(file, anchor, kind)` + ordinal within the group.

> ⚠️ **The ordinal trap, which bit once in this pass.** Inserting a callout *above* an existing one
> in the same anchor+kind group silently slides that group's blurbs down by one — every row still
> matches, so the tooling reports success while a description now sits on the wrong callout. It
> happened in `part-16` §9.4 and was caught only by reading the re-keyed rows back against the
> source lines. **Do that read-back.**

Full sequence after any guide edit:

```bash
SOURCE_DATE_EPOCH=$(git log -1 --format=%ct) ./scripts/build-indexes.sh   # re-key TSVs first
./scripts/build-skills.sh          # skills embed the indexes; a test asserts byte-equality
./scripts/verify-snippets.sh --out notes/snippet-verification   # results.tsv is keyed on (file,line) too
python3 scripts/mdlinks.py
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
```

Then bump the hardcoded callout count at `guides/README.md:74-75`
(**1,780 / 1,418** as of 2026-08-02).

**A new ```swift fence with no marker lands as `UNCLASSIFIED`.** Declaration fragments — a bare
`public mutating func …` with no enclosing type — want `illustrative`; they cannot compile
standalone.
