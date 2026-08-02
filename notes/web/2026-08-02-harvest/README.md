# Web harvest — 2026-08-02

An expansive web sweep for material that would deepen the 17-part guide series, run against the
state of the repo at commit `2ef915e` (branch `skills-codex`). **No guide was edited.** Everything
here is archival evidence plus a proposed edit list.

## Files

| File | Contents |
|---|---|
| `fm-cli-real-machine-evidence.md` | First third-party `fm --help` from a real macOS 27 build — **7 subcommands**, attested flags, the `fm serve` dispute |
| `wwdc2026-253-music-understanding.md` | Full transcript + 18 verbatim code samples for a framework with **zero corpus coverage** |
| `wwdc2026-328-mlx-swift-numerical.md` | Full transcript + 6 code samples; the one ML-track session with no corpus transcript |
| `wwdc2026-8121-ml-ai-group-lab.md` | Apple's published Q&A summaries — **settles the 4096/8192 dispute**, plus stack-layering guidance |
| `adjacent-sessions-297-375-310-256-258.md` | Five more absent sessions: Visual Intelligence, Image Playground, Shortcuts, subtitles, Xcode 27 |
| `mlx-training-and-ecosystem.md` | The third-party MLX training layer (12 algorithms, QAT), corrected release dates, Apple's M5 research post, ecosystem inventory |
| `gap-closures-and-corrections.md` | Cross-cutting: **SE-0504 closes gap G6**, `AnalyzerInput.buffer` deprecation, upstream repo drift, negative results |

---

## The seven findings that matter

### 1. ⭐ The `fm` CLI gap has third-party evidence for the first time

`part-05/references/02-fm-cli-and-python-sdk.md` carries 23 🔴 GAPs, and
`NEEDED-FROM-A-MACOS-27-MACHINE.md` item 1 is the repo's oldest open item. Three independent
authors — two English, one Japanese, spanning June–July 2026 — have run it, and one pasted
`fm --help` from **macOS 27.0 build `26A5378n`**.

Seven subcommands: `available`, `chat`, `quota-usage`, `respond`, `schema`, `serve`,
`token-count`. **Four of those seven have never appeared in this corpus.** Attested flags:
`--model pcc`, `--image <path>`, `--schema <file>`, and the `fm schema object --name <T> --string
<prop> --array` builder grammar that the guide calls "the biggest hole". Installed path
`/usr/bin/fm`.

This is third-party attestation, not first-party capture — the file recommends a 🟠 Suggestive
tier, **not** flipping any 🔴 to ✅.

### 2. ⭐ An entire framework is missing: Music Understanding

`MusicUnderstanding` returns **0 hits** across `guides/`, `notes/`, `notes/sdk-interfaces/`,
`transcripts/`, `docs/`. It is a new on-device ML framework in the 2026 release — six analysis
dimensions, `MusicUnderstandingSession`, `AsyncSequence` streaming, everything `Codable`, adopted
by Final Cut Pro. Part 1's "Apple AI stack 2026 map" is incomplete without it.

Session 253's full transcript and all 18 code samples are archived, including **four
silent-failure candidates** (the `PreferPreciseDurationAndTimingKey` quality trap, `analyze(for:)`
returning `nil` fields, `beatsPerMinute` nil below two beats, and the provider's mandatory
terminating `nil`) and **two contradictions inside Apple's own sample block**.

Proposed: a new `guides/part-16-adjacent-capabilities/references/06-music-understanding.md`,
modelled on the Speech guide, plus a Part 1 stack-map entry and four `SILENT-FAILURES.md` rows.
`scripts/dump-sdk-interfaces.sh` should be extended to capture the framework so it can be
SDK-verified rather than transcript-verified.

### 3. ⭐ Six more absent WWDC26 sessions — and a method bug that caused it

Missing and now retrieved: **328** (MLX Swift numerical computing — the *only* one of the 18
ML-track sessions with no corpus transcript), **253**, **297** (Visual Intelligence), **375**
(Image Playground), **310** (Shortcuts), **256**, **258**, **8121** (the ML & AI Group Lab).

The cause is systematic and worth fixing in `notes/FRESHNESS-RUNBOOK.md`: the corpus's session
inventory came from `developer.apple.com/wwdc26/guides/machine-learning/`, which lists **only the
18 ML-track sessions and no Group Labs**. Sessions carrying ML content in the Siri, Media and
Tools tracks were structurally invisible — the same blind spot that previously hid Tech Talk
111432. `ivan-magda/wwdc26-notes` lists 16 group labs (`8001-8007, 8009-8011, 8013-8015, 8018,
8120-8121`); **only 8120 and 8121 have been checked.**

Two full-corpus mirrors found for future sweeps: `pixelfolio/WWDC26-Transcripts` (115 of 134
sessions as Markdown, from Apple's caption tracks) and `ivan-magda/wwdc26-notes` (100+ sessions
with digests, transcripts and code, and an `llms.txt`).

### 4. ⭐ Apple settled the `contextSize` dispute

Group Lab 8121 ch. 0:08:11: **"The on-device context is 4096 tokens and is a shared budget"**;
PCC is **32K**, also shared. Three places in the repo carry the unresolved 4096-vs-8192 question
and can now cite Apple directly. The standing advice (read `contextSize` at runtime, never
hardcode) is unchanged and still correct; the device test drops in priority rather than
disappearing.

The same lab yields the cleanest available statement of the stack repositioning — Core ML "is now
focused on traditional ML like decision trees", **"anything new involving neural networks should
move to Core AI"**, Core AI "comes with SLAs and guarantees", MLX is "the place for on-device
training and distributed workloads across multiple machines" — which lands squarely on Part 1's
stack map and Part 17.5's Core ML → Core AI migration guide (15 🔴).

And it explains a contradiction the repo had already documented but not accounted for: the four
`SILENT-FAILURES.md` rows saying `permissiveContentTransformations` silently does nothing under
guided generation. Apple's answer distinguishes a **refusal** (the model's own aligned response,
"seen with guided generation") from a **guardrail error** (a separate moderation model inspecting
input *and* output). That is the missing mechanism behind the repo's finding.

### 5. ⭐ Gap G6 closed — and the guide's polyfill is a shadowing hazard

`withTaskCancellationShield` is **SE-0504, "Task Cancellation Shields", Implemented (Swift 6.4)**,
in `swiftlang/swift`'s `stdlib/public/Concurrency/TaskCancellation.swift`. The Speech guide
narrowed it to "the Concurrency library or a sample-local helper"; it is the former.

The consequence is sharper than a citation fix: §9.4's hand-written
`func withTaskCancellationShield<T: Sendable>(…)` **shadows the stdlib function** with different
generics (no typed throws, no `nonisolated(nonsending)`, an extra constraint, no async overload).
On a Swift 6.4 toolchain that is a silent substitution. The polyfill needs renaming and demoting.

### 6. MLX: training beyond LoRA is real, and it is entirely third-party

Part 12.6's three 🔴 gaps (no LoRA-vs-DoRA-vs-full quality comparison, no rank ablation, no
checkpointing overhead) **survive** — a sweep of the third-party layer found no quality ablation
either, which is worth recording as a documented negative rather than an open question.

What is new is that `mlx-lm-lora` (0 corpus references) offers **12 training algorithms** — SFT,
DPO, CPO, ORPO, GRPO, GSPO, Dr. GRPO, DAPO, Online DPO, XPO, RLHF, PPO — plus **QAT**, and
`mlx-tune` claims a **source-compatible Unsloth API** so the same training script runs on Mac or
CUDA. Nothing in the corpus currently tells a reader that preference optimisation or RL
post-training is available on Apple silicon at all.

Also corrected: MLX release dates (an HTML fetch of the releases page returned confidently wrong
*years*; the REST API is the reliable route). And Apple's own research post
`machinelearning.apple.com/research/exploring-llms-mlx-m5` — not in the corpus's URL inventory —
gives the cleanest first-party statement of the **prefill/decode asymmetry** on M5: TTFT
**3.33×–4.06×** faster, generation only **1.19×–1.27×**, explicitly because decode is
memory-bandwidth-bound. That is the right rebuttal to any "M5 is 4× faster" summary, and it
belongs in Part 15.2.

### 7. Drift, deprecations, and one deadline

- **`apple/coreai-models` is 6 commits ahead of the local clone**, including
  `ConstrainedGenerationSession` gaining **rollback, jump-forward and direct bitmask fill**
  (Part 7.4, 12 🔴), a new **`--clear-coreai-cache`** flag (Part 7.2), and the removal of
  deprecated **`LLMAsset`** terminology.
- **`AnalyzerInput.buffer` is deprecated in 27** with three watchOS-**unavailable** replacements —
  found by diffing the repo's own two Speech interfaces, and absent from the Speech guide.
- **`ImageCreator` is deprecated**; there is no headless image-generation API left.
- **iOS/Xcode 27 beta 5 was expected 2026-08-03** — the day after this harvest.
  `NEXT-BETA-CHECKLIST.md` is about to be exercised.

---

## Edit list — status as of 2026-08-02

Items 2, 3, 4, 7, 12 and the transcript half of the harvest were **implemented in a follow-up
pass**; the rest remain proposed.

| # | Edit | Guide(s) | Status |
|---|---|---|---|
| 4 | 🟠 `fm` subcommand list, flag grammar, `/usr/bin/fm`, `schema object` builder; `fm serve` dispute adjudicated; 🔴 kept for `serve` internals, `--instructions`, exit codes | 5.2 | ✅ **DONE** |
| 3 | 4096 settled with Apple's Group Lab statement; shared input+output budget and tool-definition cost added; 8192 row marked CONTRADICTED | 17.1, 3.1, 1.1 | ✅ **DONE** |
| 2 | §9.4 rewritten around SE-0504; polyfill **renamed** `withCancellationShieldCompat` to stop it shadowing the stdlib; G6 closed; checklist item 2 struck | 16.1 | ✅ **DONE** |
| 7 | Clone fast-forwarded `5ed9981` → `49becc6`. New §7.3.1 on `rollback` / `findJumpForwardString` / `fillBitmask`; new §7.1 on `--clear-coreai-cache` and the clear→probe→load→attribute measurement pattern; drift table incl. the **`.llmasset` rename** | 7.4, 7.2, 10.3 | ✅ **DONE** |
| 12 | New §13 on the third-party training layer (12 algorithms, QAT, Unsloth-compatible `mlx-tune`); the three 🔴 converted to documented ecosystem-wide negatives | 12.6 | ✅ **DONE** |
| — | Six transcripts installed: **328, 253, 297, 375, 310, 258** (`transcripts/`, 23 → 29 files) | — | ✅ **DONE** |
| 1 | Add Music Understanding to the stack map; new Part 16.6 reference guide | 1.1, 16 (new) | proposed |
| 5 | Explain the `permissiveContentTransformations` contradiction via refusal-vs-guardrail | 2.6, 17.3 | proposed |
| 6 | Add the Core ML → Core AI repositioning quote and the "choose the highest level" rule | 1.1, 17.5 | proposed |
| 8 | Record `AnalyzerInput.buffer` deprecation + watchOS gap | 16.1, 17.1 | proposed |
| 9 | Cite session 328 for the `Numerical/` examples; add the red/black-checkerboard idiom and the `eval`-in-loop rule | 13.1, 12.1 | proposed (transcript now on disk) |
| 10 | Add Visual Intelligence's two directions + `.visualIntelligence.semanticContentSearch`; verify the schema-domain count | 16.3, 16.2 | proposed (transcript now on disk) |
| 11 | Add the M5 prefill/decode asymmetry | 15.2, 12.2 | proposed |
| 13 | Add `ImageCreator` deprecation; name the Model Transcript Inspector as the empirical entity→model check | 17.1, 16.2 | proposed (transcripts now on disk) |
| 14 | Add background-inference rate-limiting as a silent failure | 15, 2.6 | proposed |
| 15 | Fix the session-inventory method in the runbook; sweep group labs 8001–8018 | — | proposed |

**Tooling run after the implemented edits** (all green): `scripts/build-indexes.sh`
(1,769 → **1,780** callouts, 1,410 → **1,418** failures; `guides/README.md` count bumped),
classified TSVs re-keyed and **11 new callouts classified**, one stale part-01 blurb asserting the
8K figure rewritten, `scripts/verify-snippets.sh` (1,358 fences, **0 failures, 0 UNCLASSIFIED**),
`scripts/build-skills.sh`, `scripts/mdlinks.py`, and the 148-test suite.

> ⚠️ **Method note for the next editor.** Editing a guide shifts every callout below the edit, and
> the classified TSVs are keyed on `(file, line, kind)`, so `build-indexes.sh` will refuse to
> build until they are re-keyed. Match on `(file, anchor, kind)` + ordinal within the group. **Watch
> the ordinal case:** inserting a callout *above* an existing one in the same anchor+kind group
> silently slides that group's blurbs down by one. That happened once here (part-16 §9.4) and was
> caught by reading the re-keyed rows back against the source lines — do the same check.

New `SILENT-FAILURES.md` candidates identified: 4 from Music Understanding, 1 from Image
Playground (`.emoji` fires a different completion and `onCompletion` never runs), 1 from Visual
Intelligence (`OpenIntent.perform` runs during foregrounding), 1 from MLX Swift (no `eval` in a
loop), 1 from the group lab (background rate-limiting), 1 from the group lab (soft natural-language
refusal that is not an error). **Nine** — none yet written, all belong to still-proposed items.

New `SILENT-FAILURES.md` candidates identified: 4 from Music Understanding, 1 from Image
Playground (`.emoji` fires a different completion and `onCompletion` never runs), 1 from Visual
Intelligence (`OpenIntent.perform` runs during foregrounding), 1 from MLX Swift (no `eval` in a
loop), 1 from the group lab (background rate-limiting), 1 from the group lab (soft natural-language
refusal that is not an error). **Nine.**

## Caveats

- Everything here is **web evidence**. Nothing was run on a macOS 27 machine, and the three items
  in `NEEDED-FROM-A-MACOS-27-MACHINE.md` that need a 27 host, an Instruments GUI recording, or a
  physical device are all still open — §7 of `gap-closures-and-corrections.md` records exactly
  which searches failed and why, so they are not repeated.
- Session transcripts fetched here are Apple's published text, retrieved directly from
  `developer.apple.com/videos/`. Group Lab 8121 is the exception: Apple publishes **no caption
  track** for labs, only editorial Q&A summaries, so it must be cited as Apple's paraphrase and
  never quoted as an engineer's words.
- Two Apple code samples in session 253 contain transcription defects (an unbalanced generic
  bracket; a task-group variable mismatch plus a scalar/array contradiction). They are preserved
  verbatim and flagged; they must not be copied into a compiled snippet —
  `scripts/verify-snippets.py` would fail hard on the first.
