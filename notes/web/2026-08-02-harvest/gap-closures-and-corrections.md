# Gap closures, corrections and drift — 2026-08-02 harvest

Cross-cutting findings that change text already written, rather than adding new territory.
Ordered by how much they change.

---

## ⭐ 1. GAP G6 CLOSED — `withTaskCancellationShield` is Swift Evolution SE-0504

**Where the gap lives:** `guides/part-16-adjacent-capabilities/references/01-speech-analyzer-end-to-end.md`
at `:1700`, `:2584` (§9.4), `:2608`, `:3039` (checklist item 2), and gap table row **G6** at `:3933`.

**What the guide currently says (row G6, verbatim):**

> **Provenance of `withTaskCancellationShield`.** *Narrowed:* it is **not** a Speech-framework
> symbol — absent from the 27.0 interface. | Appears in Apple's article and nowhere else in the
> corpus; remaining candidates are **the Concurrency library or a sample-local helper**. | Type
> the name in a scratch file with the Xcode 27 toolchain. | Write your own (§9.4) …

**The answer: the Concurrency library.** It is
[**SE-0504, "Task Cancellation Shields"**](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0504-task-cancellation-shields.md),
status **"Implemented (Swift 6.4)"**, accepted by review manager John McCall, implemented in
`swiftlang/swift` at `stdlib/public/Concurrency/TaskCancellation.swift`. Both are first-party
`swiftlang` repositories.

**Two overloads, verbatim from the proposal:**

```swift
public func withTaskCancellationShield<Value, Failure>(
  _ operation: () throws(Failure) -> Value
) throws(Failure) -> Value
```

```swift
public nonisolated(nonsending) func withTaskCancellationShield<Value, Failure>(
  _ operation: nonisolated(nonsending) () async throws(Failure) -> Value
) async throws(Failure) -> Value
```

Semantics, from the proposal: `Task.isCancelled` reads `false` inside the shielded block even when
the enclosing task is cancelled, and cancellation does not propagate through the task tree while
shielded. Motivating case is exactly the guide's: **cleanup that must run even in a cancelled
task**, where the pre-shield workaround was "creating unstructured tasks, introducing unnecessary
scheduling overhead and timing delays" — which is precisely what the guide's §9.4 fallback advice
("an unstructured `Task` already has them") recommends.

> ⚠️ **This makes the guide's polyfill actively harmful, not merely redundant.** §9.4 at `:2614`
> declares
> ```swift
> func withTaskCancellationShield<T: Sendable>(
> ```
> A same-named, same-arity global function in the user's module **shadows the stdlib one** with
> different generics (no typed throws, no `nonisolated(nonsending)`, an extra `Sendable`
> constraint the real API does not impose, and no async overload pairing). On a Swift 6.4
> toolchain that is a silent behavioural substitution.
>
> **Recommended edit to §9.4:** lead with SE-0504 and the real signatures; demote the polyfill to
> "only if you must target a pre-Swift-6.4 toolchain", and rename it in that case
> (e.g. `withCancellationShieldCompat`) so it cannot shadow. Delete checklist item 2 at `:3039`
> ("Type `withTaskCancellationShield` in a scratch file. Does it resolve?") — it is answered.

**Residual:** which Xcode 27 beta ships Swift 6.4 was not confirmed. That is a one-line local
check (`xcrun swift --version`), not a research question.

## ⭐ 2. The 4096-vs-8192 `contextSize` dispute — Apple has now stated 4096 for iOS 27

Covered in full in `wwdc2026-8121-ml-ai-group-lab.md` §1. Summary of the edit surface:

| File | Line | Change |
|---|---|---|
| `part-17/01-what-changed-checklist.md` | 180–183 | 🟡 "Apple has not corroborated 8192 anywhere we can find" → **Apple has now corroborated 4096**, WWDC26 Group Lab 8121 ch. 0:08:11 |
| `part-17/01-what-changed-checklist.md` | 2571 | Same row in the summary table |
| `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` | item 7 | Keep the device test; **downgrade its priority** — it is now a check against an explicit Apple statement, not an open question |

New, additive: the budget is **shared across input and output** with Apple's worked example
("feed in 4000 tokens, the response can use the remaining ~96"), and **tool definitions and
instructions consume the same budget** (ch. 0:39:42). Part 3.1 (context window and KV cache) should
carry both.

## 3. NEW — `AnalyzerInput.buffer` is **deprecated in 27**, and the Speech guide does not say so

**Source: the repo's own SDK captures**, not the web. `diff notes/sdk-interfaces/Speech-26.5-macos.swiftinterface
notes/sdk-interfaces/Speech-27.0-macos.swiftinterface` (682 → 742 lines) shows:

```swift
@available(anyAppleOS, deprecated: 27, message: "use other AnalyzerInput properties to get information about audio")
public var buffer: AVFAudio::AVAudioPCMBuffer { … }
```

with three iOS-27-only, **watchOS-unavailable** additions replacing it:

```swift
@available(anyAppleOS 27, *) @available(watchOS, unavailable)
public init(buffer: CoreMedia::CMReadySampleBuffer<CoreMedia::CMReadOnlyDataBlockBuffer>)

@available(anyAppleOS 27, *) @available(watchOS, unavailable)
public let bufferDuration: CoreMedia::CMTime

@available(anyAppleOS 27, *) @available(watchOS, unavailable)
public let bufferFormat: AVFAudio::AVAudioFormat
```

**Grep result:** `grep -n "deprecated: 27" guides/part-16-.../01-speech-analyzer-end-to-end.md`
returns **nothing**. The three new symbols *are* covered (`bufferDuration` 3 guides,
`CMReadySampleBuffer` 1), but the **deprecation of the thing they replace is not**, and neither is
the watchOS unavailability of all three.

This is a Part 17 (migration) item as much as a Part 16 one: a 26-era `AnalyzerInput` consumer that
reads `.buffer` compiles with a deprecation warning on 27 and has **no replacement on watchOS**.
That last part is the sharp edge — the migration is not uniformly available across platforms.

**Method note worth recording in the runbook:** this was found by diffing two interfaces already
sitting in `notes/sdk-interfaces/`, after the web returned nothing on Speech-in-27 (see §7).
`scripts/diff-interfaces.sh` diffs a fresh capture against git; there appears to be **no routine
that diffs the committed 26.5 baseline against the committed 27.0 capture** looking for
`deprecated:` annotations. A one-line grep for `deprecated: 27` across all 27.0 interfaces would
likely surface more of these.

## 4. DRIFT — `apple/coreai-models` has moved 6 commits past the local clone

Local clone `repos/apple__coreai-models` is at `5ed9981` (2026-07-23). Upstream since:

| Date | SHA | Message |
|---|---|---|
| 2026-07-31 | `49becc6c` | **"Extend `ConstrainedGenerationSession` with rollback, jump-forward, and direct bitmask fill"** |
| 2026-07-31 | `c7421ba1` | "remove unneeded flux2 text encoder float cast before quantization" |
| 2026-07-31 | `f3e86898` | "Fix compiler warnings from **macOS 27 Beta 4 SDKs**" |
| 2026-07-29 | `aa3bbf6b` | **"Add `--clear-coreai-cache` flag to clear Core AI specialization cache before model load"** |
| 2026-07-29 | `367ad527` | **"New custom op for KV cache update"** |
| 2026-07-28 | `86b4c04e` | **"Remove Deprecated `LLMAsset` Terminology"** |

Three of these land directly on guide text:

- **`ConstrainedGenerationSession` + rollback / jump-forward / bitmask fill** →
  Part 7.4 (`04-bundles-engines-and-guided-decoding.md`, 12 🔴). Jump-forward decoding and
  rollback are *semantically significant* guided-decoding features, not refactors.
- **`--clear-coreai-cache`** → Part 7.2 (`02-specialization-caching-and-aot.md`). A new escape
  hatch for the specialization cache; also relevant to the `AIModelCache` deletion-semantics
  question in `NEEDED-FROM-A-MACOS-27-MACHINE.md` item 7.
- **`LLMAsset` terminology removed as deprecated** → grep the guides for `LLMAsset`; any occurrence
  is now stale nomenclature.

`git -C repos/apple__coreai-models pull` and re-read is the action. Other clones are also worth
refreshing: `mlx` (2026-07-24), `mlx-lm` (2026-07-26), `coreai-torch` (2026-07-23),
`coreai-optimization` (2026-07-24), `python-apple-fm-sdk` (2026-07-07),
`mlx-swift-examples` (2026-06-15).

## 5. NEW deprecation — `ImageCreator` (Image Playground)

From WWDC26 session 375: "**`ImageCreator`, the non-UI API for generating images directly in your
code, is deprecated.**" Detail in `adjacent-sessions-297-375-310-256-258.md` §375. Belongs in
Part 17's what-changed checklist next to the adapter sunset and the `GenerationError` deprecation.
The capability consequence — **no headless image generation path remains** — is the part worth
stating plainly.

## 6. TIMING — iOS/Xcode 27 **beta 5** was expected 2026-08-03

Multiple beta-tracking sources put iOS 27 beta 5 at **on or around Monday 2026-08-03** — i.e.
**tomorrow, relative to this harvest**. Beta 4 is `24A5390f`, released 2026-07-20; no beta 5 build
number was published at fetch time.

**Action:** `notes/NEXT-BETA-CHECKLIST.md` is about to be exercised. Re-run
`scripts/dump-sdk-interfaces.sh` and `scripts/diff-interfaces.sh` once beta 5 is installed, and
fold the `deprecated: 27` sweep from §3 into that pass.

## 7. Negative results — record these so nobody re-searches them

| Question | Searched | Outcome |
|---|---|---|
| What changed in **Speech** for iOS 27? | 5 queries across community blogs, Argmax/WhisperKit, MacStories, forums | **The community has written nothing about Speech in 27.** Every result is WWDC25/iOS 26 material. The SDK diff (§3) is the only source. |
| `maximumReservedLocales` **value** | web + SDK | Interface declares `public static var maximumReservedLocales: Swift::Int` — a **computed property**, so the value is not in the interface. Still a runtime probe. Guide's 🔴 at `:1243` stands. |
| Instruments 27 **lane names** / Core AI Debugger | session 258 fetched in full | 258 is entirely about **coding agents**; no Instruments, no Core AI Debugger. `NEEDED-FROM-A-MACOS-27-MACHINE.md` item 3 unchanged. |
| Does system **generated-subtitles** expose a Speech API? | session 256 fetched in full | **No.** System-level, automatic, `MediaAccessibility`-styled only. |
| LoRA-vs-DoRA-vs-full **quality** ablation | mlx-lm, mlx-lm-lora, mlx-tune, awesome-mlx sweep | **Does not exist** in the third-party layer either. Part 12.6 `:1211` / `:1464` stand as documented negatives. |
| `fm serve` existence | two conflicting sources | Contested — see `fm-cli-real-machine-evidence.md` §4. A pasted `--help` from build `26A5378n` lists it; one commentator argues from transcript-absence that it does not exist. |

## 8. One source to distrust

`chatforest.com/builders-log/apple-fm-cli-python-sdk-fm-serve-openai-compatible-psotu-wwdc-2026/`
prints a self-correction retracting its own earlier `fm serve` claim, then argues the subcommand
does not exist **on the grounds that it is absent from Apple's session transcript**. That is the
inference this repo's house style explicitly forbids, and it is contradicted by a pasted `--help`
from a named macOS 27.0 build. Its Python-SDK details (§6 of the fm file) may still be usable but
should be checked against the already-cloned `repos/apple__python-apple-fm-sdk`, which outranks it.
Consider adding it to the "unreliable sources" section of `notes/web/community-blogs.md` §9 with
this reasoning attached.
