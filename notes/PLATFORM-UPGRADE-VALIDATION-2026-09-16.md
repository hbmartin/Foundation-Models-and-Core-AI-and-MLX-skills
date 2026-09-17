# Platform upgrade validation — 2026-09-16

This is the canonical documentation summary of the macOS 27 and physical-iPhone validation run.
Raw logs and result bundles remain under `artifacts/freshness/`; those artifacts are ignored and
machine-local, so claims promoted into guides should cite this note or the probe source that emits
the result.

## Outcome

- The safe local-Mac runtime surface passed: **44 of 46 probes executed and passed** across bounded
  lanes. PCC construction and the interactive Instruments workload were intentionally excluded.
- The physical iPhone 15 Pro run passed **46 tests, 2 intentional skips, 0 failures** in 853.299 s.
- Daily freshness completed. Weekly freshness completed its independent checks but was marked
  blocked only because the retired Noema mirror no longer resolved. That mirror has now been
  removed from the clone inventory.
- Repository tests passed **253/253** before this documentation promotion. The two-SDK snippet
  matrix remains blocked because the configured Xcode 26 path is absent.

## Observed environment

| Component | Observed | Interpretation |
|---|---|---|
| macOS | 27.0 (`26A428`) | Matches the public macOS 27.0 build. |
| Selected Xcode | 27.0 beta 5 (`27A5237l`) | Older than Xcode 27 final (`27A266a`) and Xcode 27.2 beta (`27B5019j`). |
| macOS / iPhoneOS SDK | 27.0 (`26A5406c` / `24A5408c`) | Both come from beta-5 Xcode. |
| Newest installed simulator | iOS 27.0 beta 5 (`24A5408d`) | Not a current public runtime. |
| Physical device | iPhone 15 Pro, `D83AP`, `h16p`, iOS 27.0 (`24A435`) | Does not match the public iOS 27.0 build `24A437`; treat it as a distinct observed build. |
| `/usr/bin/fm` | Present on stable macOS | Stable help surface has seven commands and exposes only the `system` model. |

The latest Apple releases observed on 2026-09-16 were Xcode 27.2 beta `27B5019j`, iOS 27.2 beta
`24B5084k`, and macOS 27.2 beta `26B5086k`. The installed environment is therefore deliberately
recorded as mixed stable-OS/beta-toolchain evidence, not promoted as a coherent final SDK capture.

## Stable `fm` CLI drift

Compared with the committed macOS 27 beta-5 capture, stable macOS 27 removed `quota-usage`, the
`pcc` model choice, and `--model pcc`. Its top-level commands are:

`available`, `chat`, `count-tokens`, `license`, `respond`, `schema`, and `serve`.

The stable help surface advertises only the `system` model. This is a CLI-surface observation; it
does not establish that PCC itself was removed from Foundation Models. Guides must not recommend
`--model pcc` on stable macOS 27.

## Foundation Models runtime observations

- Model availability, `contextSize=4096`, vision, tool calling, and guided generation matched on
  Mac and device; reasoning was unavailable.
- Call-site `GenerationOptions.toolCallingMode` overrode the profile in **both directions**. With
  profile-required/options-disallowed no tool ran. With profile-disallowed/options-required the
  tool ran, then the turn ended in `contextSizeExceeded(4096,4099)`.
- Throwing from `onToolCall` prevented the tool body, caused `respond` to throw `ToolCallError`,
  and reverted the failed turn to an instructions-only transcript. It is a turn-abort hook, not an
  interactive-consent loop.
- A large overflow returned typed `contextSizeExceeded` on Mac after 92.7 s; the corresponding
  device probe timed out at 120 s. Code still needs an outer deadline.
- Normal labeled and unlabeled image responses succeeded and labels were recorded as expected.
  Every tested image size (128–1792 px) made `tokenCount(for:)` throw `LanguageModelError -1`.
  Required image-tool turns timed out after the tool body ran on both Mac and device.
- The unreachable `SampleGenerator` case finished with zero samples, three provider invocations,
  and 17 rejected samples on both destinations.
- `am_ET` produced `LanguageModelError.guardrailViolation`, not
  `unsupportedLanguageOrLocale`, on both destinations.
- Nil transcript policy matched `.revert`; `.preserve` retained the prompt and tool call after a
  failed turn. Breaking a stream after two partials left `isResponding=true` at observation time.

## Core AI and Spotlight observations

- Deleting a cache entry while a live model retained it threw a dynamic
  `AIModelCacheError.failedToPurge`; the entry stayed findable. Deletion succeeded after release.
- A 12 KiB source asset grew the default cache by 24 KiB. This is a fixture observation, not a
  general 2× sizing rule.
- The cancellation probe completed after 10 s and left a cache entry, so cancellation semantics
  remain inconclusive. Returned specialization and later lookup resolved to the same entry.
- Default specialization allowed CPU, GPU, and Neural Engine with
  `expectFrequentReshapes=false`. Six NDArray rounds were zero but remain inconclusive.
- The Spotlight tool schema stayed at 83,570 characters. Donation/cleanup succeeded on simulator
  and device but failed on the Mac host with `CSIndexErrorDomain -1003` because the helper app was
  unavailable.

## Freshness jobs

The daily sweep saw 426 references and 1,008 sightings: 260 ambiguous, 163 unchanged, three
state-changed, and zero unreachable. The three reported closures were already incorporated on the
then-current main branch. The weekly sweep saw 428 references and 1,010 sightings: 262 ambiguous,
166 unchanged, zero state-changed, and zero unreachable. Default Mac probes passed 46 tests with
26 expected skips; simulator probes passed 39 with 22 expected skips. No eligible automatic change
or pull request was produced.

## Remaining boundaries

1. Re-run the physical-device lane on public iOS build `24A437` or the intended newer beta.
2. Install/select a coherent Xcode/runtime track before replacing the committed SDK interfaces.
3. Restore Xcode 26 if the full dual-SDK snippet matrix remains policy.
4. Record the remaining Instruments GUI workload.
5. Keep explicit deadlines around slow overflow and required image-tool turns.

Source artifacts: `artifacts/freshness/reports/20260916-platform-upgrade-validation.md`, daily run
`20260916T224807Z-18269`, weekly run `20260916T224834Z-18484`, Mac beta-event runs beginning
`20260916T231100Z`, and device run `20260916T225700Z-device`.
