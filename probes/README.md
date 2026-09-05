# probes/ — runtime probes for the open behavioral gaps

A SwiftPM package whose XCTest cases are **executable evidence collectors**: one probe per
open 🔴 GAP in the guide series that a machine can decide. The package **builds and tests
green on the authoring host today** (macOS 27 beta 5 `26A5406e`, Xcode 27 beta 5
`27A5237l`), and its hosted runner has completed a first physical-device baseline on an iPhone 15
Pro running iOS 27 build `24A5408d`. On each new beta or runtime update, the same tests turn
behavioral drift into log lines.

**Output contract.** Probes never fake a pass/fail. A measuring probe prints

```
PROBE-RESULT name=<gap-id> value=<...> detail=<...>
```

and passes; a branch probe (two documented-contradictory behaviors) asserts nothing and
prints which branch actually happened. Harvest every `PROBE-RESULT` line back into the
guide section named in the probe's doc comment — each doc comment states the gap, the
candidate answers, and what to write back for each outcome.

## How to run

| Destination | Meaning | Command |
|---|---|---|
| **HOST-26** | today's host, macOS 26.6 | `./scripts/run-probes.sh host` |
| **SIM-27** | pinned iOS 27.0 Simulator on today's host | `./scripts/run-probes.sh simulator` (override with `--destination` or `PROBE_SIMULATOR_DESTINATION`) |
| **MAC-27** | upgrade day, a Mac running macOS 27 | `./scripts/run-probes.sh host` |
| **DEVICE-27** | physical iPhone/iPad on 27 with Apple Intelligence | Use the hosted device mode shown below; a bare Swift-package test bundle is tool-hosted and Xcode refuses it on hardware. |

## Generated baseline summary

<!-- current-state:probes:start -->
- `app-hosted-ios27-beta5-simulator` — app-hosted; iOS Simulator 27.0 beta 5 (24A5408d); Xcode 27.0 beta 5 (27A5237l); destination `generated DeviceProbes app`; device `Simulator`; 39 tests / 19 skipped / 0 failures; contextSize=0. The 2026-09-04 app-hosted pass returned 0; this now agrees with the latest tool-hosted pass but not its earlier 4096 result.
- `device-hosted-iphone15pro-ios27-beta5` — device-hosted; iOS 27.0 beta 5 (24A5408d); Xcode 27.0 beta 5 (27A5237l); destination `wired physical device`; device `iPhone 15 Pro (iPhone16,1; D83AP)`; 11 tests / 4 skipped / 0 failures; contextSize=4096. Offline/static pass; a separate asset pass ran four tests with zero failures.
- `tool-hosted-ios27-beta5-simulator` — tool-hosted; iOS Simulator 27.0 beta 5 (24A5408d); Xcode 27.0 beta 5 (27A5237l); destination `iPhone 17 Pro, OS=27.0`; device `Simulator`; 39 tests / 19 skipped / 0 failures; contextSize=0. The 2026-09-05 tool-hosted pass returned 0, while the 2026-08-17 pass returned 4096 on the same recorded builds; treat this value as volatile. Build-keyed model skips are active.
- `tool-hosted-macos27-beta5` — tool-hosted; macOS 27.0 beta 5 (26A5406e); Xcode 27.0 beta 5 (27A5237l); destination `local arm64 host`; device `Mac host`; 46 tests / 23 skipped / 0 failures; contextSize=4096. Reverified 2026-09-05; build-keyed model, attachment, and unreachable-generator skips are active.
<!-- current-state:probes:end -->

Every result below must be interpreted against one of these complete topology tuples. A measured
value from one hosting mode is not a default for another hosting mode, even on the same runtime.

`run-probes.sh` puts the SwiftPM scratch directory or DerivedData, logs, direct probe artifacts,
and simulator/device `.xcresult` in a unique ignored
`artifacts/freshness/<automation-id>/<UTC-run-id>/` directory. Host and simulator runs use the
same tool-hosted Swift-package lanes as the recorded baselines. For simulator runs, the wrapper
builds first and injects supported shell-prefixed `PROBE_*` variables into the generated
`.xctestrun` before launch; Xcode does not forward those variables from its own shell environment.
Physical-device XCTest instead needs the app host generated from the committed XcodeGen spec. Use
the device UDID from `xcrun xctrace list devices` (or the `Hardware: UDID` field from `xcrun
devicectl device info details`):

```bash
./scripts/run-probes.sh device \
  --destination 'platform=iOS,id=<device-udid>' \
  --team-id <your-team-id>
```

Keep the phone unlocked through destination preflight. The former
`xcodebuild test -scheme Probes-Package -destination 'platform=iOS,…'` command fails before launch
with `Tool-hosted testing is unavailable on device destinations`; the generated project supplies
the required minimal `DeviceProbeHost` app. XcodeGen is available from Homebrew (`brew install
xcodegen`). The host is probe infrastructure only and displays no data.

Environment knobs:

- `PROBE_AIMODEL_URL=/path/to/model.aimodelc` — unlocks the four asset-dependent Core AI
  cache probes (they `XCTSkip` without it). For DEVICE-27, copy the asset directory into
  `probes/DeviceProbeAssets/` before generating the project. The device runner auto-selects it
  when exactly one `.aimodel` or `.aimodelc` is present because shell environment variables do not
  propagate through this physical-device test launch; if several are bundled, it resolves the
  requested host path by its last path component. Scheme-declared test environment variables DO
  reach the device process: `device-project.yml` declares the device-relevant `PROBE_*` knobs on
  the `DeviceProbes` scheme, disabled by default, so `xcodegen generate` preserves the
  declarations — tick one in the scheme editor for a one-off run (the tick itself does not
  survive regeneration), or flip its `isEnabled` to `true` in the spec before regenerating.
  Assets in that directory are ignored by Git. Produce one with
  `xcrun coreai-build compile … --output …` (ships in the optional Metal Toolchain
  component — `xcodebuild -downloadComponent MetalToolchain`; see
  `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 2) or `xcrun aimodelc`.
- `PROBE_ENUM_RUNS=100` — sample count for the `.anyOf` enforcement probe (default 10).
- `PROBE_CONCURRENT_SESSIONS=16` — width of the concurrent-session probe (default 8).
- `PROBE_ENABLE_PCC=1` — opt-in for the PCC probe (an unentitled process may `fatalError`
  constructing PCC — guide 2.6 §8.5 — so it is off by default to keep the suite crash-safe).
  Declared, disabled, on the `DeviceProbes` scheme in `device-project.yml` so it can reach its
  only listed destination, a physical-device test process.
- `PROBE_INSTRUMENTS_WORKLOAD=1` — unlocks the Instruments recording workload
  (`instruments.fm-workload`; see `INSTRUMENTS-RECORDING.md`). Companions:
  `PROBE_WORKLOAD_SECONDS` (default 300) and `PROBE_WORKLOAD_ATTACH_SECONDS` (default 20).
- `PROBE_ARTIFACT_DIR=/absolute/output/path` — writes complete probe artifacts when a destination
  can access that path. The runner supplies its durable `ProbeArtifacts/` path automatically for
  host and tool-hosted simulator runs. App-hosted physical-device tests cannot write to a host
  path; `fm.spotlight-tool-surface` therefore also attaches its complete schema to the `.xcresult`.
- `PROBE_ENABLE_ATTACHMENT=1` — retries the image-attachment probe on the macOS 27 beta-5 host or
  iOS 27 beta-5 Simulator. Both block inside image tokenization by default on the 2026-08-17
  runtime, before an async timeout can execute, so weekly runs skip this probe there.
- `PROBE_ENABLE_GENERATOR=1` — retries the unreachable-target `SampleGenerator` probe on the
  macOS 27 beta-5 host or Simulator. The host call blocks non-cancellably; Simulator can consume
  nearly the full timeout and poison subsequent host-backed model calls. Physical devices remain
  enabled by default.
- `PROBE_ENABLE_HOST_MODEL=1` — retries model-dependent Foundation Models probes on the macOS 27
  beta-5 host or Simulator. The host-backed runtime reports `.available`, but generation calls can
  block before test timeouts execute; offline/static probes remain enabled without this override.

**Instruments lane-name capture** (the one manual GUI session): `INSTRUMENTS-RECORDING.md`
— workload command, attach procedure, transcription checklist, write-back list. A
standalone fallback binary lives in `Workload/fmworkload.swift` (outside the package).

**SIM-27 deep pass** (higher sample counts): prefix the SIM-27 command with
`PROBE_ENUM_RUNS=100 PROBE_CONCURRENT_SESSIONS=16` — the wrapper transfers those values into
the generated `.xctestrun` before starting XCTest.

**Verified 2026-08-03 (host now macOS 26.6 `25G72`):** `swift test` on the host —
46 tests, 34 skipped, 0 failures, exit 0. SIM-27 full run — 39 tests, 2 skipped (PCC
opt-in + the env-gated Instruments workload), 0 failures, `TEST SUCCEEDED`. All five
host-runnable PROBE-RESULT values matched their 26.5 baselines on 26.6 — no behavioral
drift from the 26.5.2 → 26.6 host update.

**Verified 2026-08-17 (macOS 27 beta 5 `26A5406e`, Xcode `27A5237l`):** the default bounded
host run is **46 tests, 23 skipped, 0 failures**; the iOS 27 Simulator (`24A5408d`) run is
**39 tests, 19 skipped, 0 failures**, `TEST SUCCEEDED`. Beta 5 reports its host-backed model
available while some generation and image-tokenization calls block non-cancellably. The default
suite therefore skips model-dependent, attachment, and unreachable-generator probes on host-backed
destinations **while they remain on these two builds** — the gate is keyed to the recorded build
identifiers, so a runtime update re-enables those probes by default and the counts above describe
gated beta-5 runs only; the three `PROBE_ENABLE_*` overrides force earlier retries (e.g. after a
service restart on the same build). Offline/static `PROBE-RESULT` values remained stable except that Spotlight's unpublished
schema grew from 83,494 to 83,570 characters. Simulator donation and cleanup still work; on the
host, both fail because the Spotlight helper is unavailable (`CSIndexErrorDomain -1003`).

**Verified 2026-09-04 (app-hosted Simulator runner):** the generated `DeviceProbes` project
completed **39 tests, 19 skipped, 0 failures**, `TEST SUCCEEDED`. Offline/static values matched
the beta-5 baseline except `fm.contextSize`: the app-hosted Simulator process returned **0**, while
the earlier tool-hosted `Probes-Package` run returned **4096** on the same `24A5408d` runtime.
Treat context size as runner-context-sensitive until a later runtime or device pass explains it.

**Reverified 2026-09-05 (tool-hosted host and Simulator runners):** the host completed **46
tests, 23 skipped, 0 failures** and returned `contextSize=4096`; the Simulator completed **39
tests, 19 skipped, 0 failures** and returned `contextSize=0`. The latter contradicts the
2026-08-17 tool-hosted Simulator result of 4096 despite the same recorded OS/runtime and Xcode
builds, so hosting mode alone does not explain the value. Preserve both observations and treat the
property as runtime evidence, never as a hardcoded platform constant.

**Verified 2026-08-20 (iPhone 15 Pro `iPhone16,1` / `D83AP`, iOS 27 build `24A5408d`, wired):**
the hosted XCTest runner launched successfully. The offline/static pass completed 11 tests with 4
asset skips and 0 failures; a second pass with a bundled 12,288-byte portable toy `.aimodel`
completed all 4 asset-dependent Core AI tests with 0 failures. The device reported
`contextSize=4096`, `deviceArchitectureName=h16p`, and `expectFrequentReshapes=false` for both
`.default` and `.cpuOnly`. Cache deletion threw while a live model pinned the entry, the entry
remained findable, and deletion succeeded after release. The cache-location and cancellation
measurements below are deliberately bounded to what the tiny fixture can establish.

## Probe inventory

Guide refs abbreviated: `2.3 §4.4` = `guides/part-02-…/references/03-… .md` §4.4.
Status: ✅ answered (result below) · 🟠 partially answered on SIM-27, needs a clean
MAC-27/DEVICE-27 pass · ⏳ compiled, waiting for its destination · 🔒 also needs an env
knob (asset/entitlement).

| Probe id | Gap | Guide § | Destination | Status |
|---|---|---|---|---|
| `fm.tool-schema-flag-default` | `Tool.includesSchemaInInstructions` default value | 2.3 §4.4 + NEEDED item 5 | HOST-26 · SIM-27 · MAC-27 · DEVICE-27 | ✅ `true` on host, sim, and device |
| `fm.tool-derived-name` | derived `Tool.name` string | 2.3 §2 | HOST-26 · SIM-27 · DEVICE-27 | ✅ verbatim type name on every tested runtime |
| `fm.contextSize` | 4096 vs 8192 on 27 | NEEDED item 7 · 3.1 | HOST-26 · SIM-27 · DEVICE-27 | 🟠 4096 on host and iPhone 15 Pro; both Simulator modes most recently returned 0. Tool-hosted Simulator observations changed from 4096 (2026-08-17) to 0 (2026-09-05) on the same recorded builds. |
| `fm.availability` | does FM work against the Simulator | 5.1 §13.4 · 17.2 | HOST-26 · SIM-27 | ✅ sim: `available`, inference runs |
| `fm.toolCallingMode-precedence` | options vs profile modifier | 2.6 §7.4 · 17.1 §4.8 | MAC-27 / DEVICE-27 | 🟠 device confirms options `.disallowed` beats profile `.required` (tool not called); the reverse direction is NOT yet a recorded observation — the 2026-08-20 run threw `contextSizeExceeded(4096, 4099)` and the catch path recorded no toolCalled/toolRan discriminators, so "the tool loop ran" is an inference from the fingerprint. The probe now records them for the next device run |
| `fm.includeSchemaInPrompt-recording` | legacy param vs `ContextOptions` | 17.1 §4.11 | SIM-27 · MAC-27 · DEVICE-27 | ✅ one knob, two spellings; default `true` |
| `fm.error-domain-context-overflow` | error type/domain table row | 17.3 §6.3 | SIM-27 · MAC-27 · DEVICE-27 | ✅ `LanguageModelError.contextSizeExceeded`, code 0 |
| `fm.parsingError-thrown` | is `GeneratedContent.ParsingError` thrown | 17.3 §4.4 · 17.1 ledger 9 | SIM-27 · MAC-27 · DEVICE-27 | ✅ YES, thrown on truncation |
| `fm.stream-early-break` | transcript after early `break` | 2.2 ledger 8 | SIM-27 · MAC-27 · DEVICE-27 | ✅ partial response entry lands; `isResponding` stays true |
| `fm.collect-after-iteration` | `collect()` after manual iteration | 2.2 ledger 7 §9.3 | SIM-27 · MAC-27 · DEVICE-27 | ✅ allowed, returns full response |
| `fm.image-token-cost` | tokens per image; the 896 px hypothesis | 3.1 §2.4 + ledger | MAC-27 / DEVICE-27 | 🟠 device: text=6, all six image sizes throw `LanguageModelError -1`; cost remains unknown |
| `fm.concurrent-session-limit` | concurrent-session ceiling | 2.1 §8 | SIM-27 · MAC-27 / DEVICE-27 | 🟠 sim + device: 8/8 ok, no ceiling at n=8 |
| `fm.onToolCall-throw-effect` | per-call veto vs turn abort | 3.4 §6 | MAC-27 / DEVICE-27 | ✅ device: tool body does not run; whole turn throws `ToolCallError` and reverts |
| `fm.required-mode-no-tools` | `.required` with empty toolset | 3.4 §6 · 2.6 §7.4 | SIM-27 · DEVICE-27 | ✅ both throw, but bridge differs: sim generic code −1; device typed `.unsupportedGenerationGuide`, code 6 |
| `fm.transcript-policy-nil-default` | which policy `nil` selects | 17.3 §2.2 · 17.1 ledger 5 | SIM-27 · MAC-27 · DEVICE-27 | ✅ `nil` behaves like `.revertTranscript` |
| `fm.pcc-availability` | PCC vs Siri-disabled; PCC-in-sim | 4.1 §5.8 | DEVICE-27 (manual Siri toggle) | 🔒 `PROBE_ENABLE_PCC=1` |
| `fm.anyOf-enum-enforcement` | `.anyOf` constrained or advisory | 2.2 §4.6 | SIM-27 · MAC-27 · DEVICE-27 | 🟠 sim + device: 20/20 aggregate runs, 0 violations (constrained reading; still a small N) |
| `fm.guardrails-permissive-generable` | permissive guardrails on `@Generable` | 2.2 §11.3 ledger 13 · 17.3 | MAC-27 / DEVICE-27 | 🟠 device: both settings succeeded; probe did not trip a guardrail, so effect remains unresolved |
| `coreai.deviceArchitectureName` | authoritative arch codes | 15.1 §4.4 | MAC-27 · DEVICE-27 (**no sim** — see below) | ✅ iPhone 15 Pro `iPhone16,1` / `D83AP` = `h16p` |
| `coreai.specializationOptions-defaults` | `expectFrequentReshapes` default; compute-unit sets | 7.1 §4.3, §16.3-7 | MAC-27 · DEVICE-27 | ✅ device: default and cpuOnly both `false`; allowed units recorded below |
| `coreai.ndarray-zero-init` | does `NDArray(shape:scalarType:)` zero storage | 7.3 §8.3 | MAC-27 · DEVICE-27 | 🟠 six 8 MiB device allocations were all zero; still not an initialization contract |
| `coreai.cache-delete-while-referenced` | delete throws vs defers | 7.2 §7 + NEEDED item 7 | MAC-27 / DEVICE-27 | ✅ device: throws while live, remains findable, succeeds after release |
| `coreai.specialize-cancellation` | is specialization cancellable | 7.2 §5 · 17.6 §5 | MAC-27 / DEVICE-27 | 🔒 tiny device fixture completed before cancellation; retry with a slow asset |
| `coreai.cache-location-size` | cache location and entry size | 7.2 §6 | MAC-27 / DEVICE-27 | 🟠 default cache observed at `Library/Caches/coreai-cache`; one toy-model size result below |
| `coreai.specialize-return-identity` | `specialize()` return vs `model(for:)` | 7.2 §9 | MAC-27 / DEVICE-27 | 🟠 default cache: identical 181-byte bookmarks; entitled app-group variant remains |
| `eval.metric-identity` | `Metric` identity: name or instance | 6.1 §8.2, §17 | SIM-27 · MAC-27 | ✅ BY NAME |
| `eval.mean-over-all-ignored` | mean over zero scored samples | 6.1 §17.5 | SIM-27 · MAC-27 | ✅ sentinel `-1.0` |
| `eval.subject-throws` | per-sample subject failure handling | 6.1 §17.7 | SIM-27 · MAC-27 | ✅ run continues; failures excluded from aggregate |
| `eval.disallowed-arguments-narrowing` | do `disallowed` matchers narrow | 6.3 | SIM-27 · MAC-27 | ✅ YES, arguments narrow |
| `eval.allowsAdditionalCalls-false` | semantics of `false` | 6.3 ledger | SIM-27 · MAC-27 | ✅ enforced; extra call fails `allPass` |
| `eval.generator-unreachable-target` | unreachable `targetCount` behavior | 6.3 §3, §5 | SIM-27 · MAC-27 | ✅ gives up after retry budget, finishes short |
| `speech.assetInventory-status-order` | `Status` `Comparable` ordering per OS generation | 16.1 §5.2 · G2 · NEXT-BETA §7 | HOST-26 · SIM-27 · MAC-27 · DEVICE-27 | ✅ **ordering DIFFERS** — 26: `unsupported<supported<downloading<installed`; 27 sim + device: `unsupported<downloading<supported<installed` (`<` is synthesized) |
| `fm.capabilities` | does `capabilities` reflect per-destination reality | 5.1 §13.4 | SIM-27 · MAC-27 · DEVICE-27 | 🟠 sim + device claim vision/tool-calling/guided-generation and no reasoning; attachment device probe hit tokenizer failures, so treat as declaration |
| `fm.attachment-label-recording` | `.label(_:)` token cost / transcript write-through / tool no-op | 2.5 §6.4 · 2.3 | MAC-27 · DEVICE-27 | 🟠 device: token count errors; responses work; labels write through exactly; generic tool runs labeled and unlabeled, then required loop times out |
| `fm.stream-zero-partials-tool-turn` | tool-only turn yields zero partials? | 2.1 §6.4 · 2.2 §9.6 · SILENT-FAILURES | MAC-27 · DEVICE-27 | 🟠 device tool ran, but required loop ended in `contextSizeExceeded` before proving zero-partial completion |
| `fm.unsupportedLanguageOrLocale-error` | is the error ever thrown for unsupported locales | 17.3 §6.3 · 2.6 | SIM-27 · MAC-27 · DEVICE-27 | 🟠 `am_ET`: sim silently succeeds; device throws a guardrail violation, not unsupported-locale — named case still unobserved |
| `fm.spotlight-tool-surface` | declared name + unpublished `parameters` schema | 2.4 §7 · 2.3 §2 | SIM-27 · MAC-27 · DEVICE-27 | ✅ `spotlight_search`, `includesSchema=true`, beta-5 schema 83,570 characters on sim + device |
| `fm.spotlight-direct-call` | donation + direct `call()` from the runner container | 2.4 §7/§7.1 | SIM-27 · MAC-27 · DEVICE-27 | ✅ sim + device donation works; all three encodings rejected **in-band** (code-100 JSON, never throws); 3 replies observed |
| `instruments.fm-workload` | Instruments recording target (not a measurement) | 5.1 §6.3 · NEEDED item 3 | SIM-27 (manual) · MAC-27 | 🔒 `PROBE_INSTRUMENTS_WORKLOAD=1`; procedure in `INSTRUMENTS-RECORDING.md` |

## Results harvested 2026-08-20 (physical iPhone)

Destination: iPhone 15 Pro (`iPhone16,1`, hardware `D83AP`), iOS 27.0 build `24A5408d`,
Xcode 27 beta 5 (`27A5237l`). The asset pass used a 12,288-byte portable linear/ReLU toy model
with one `float32[1,4]` input and output. It is intentionally useful for cache semantics, not for
timing or cancellation conclusions. Lines below preserve the exact `value` and compact `detail`;
the complete console and large Spotlight reply payload remain in the ignored `.xcresult` bundle.

```
PROBE-RESULT name=fm.contextSize value=4096 detail=os=27.0.0 platform=iOS
PROBE-RESULT name=fm.availability value=available detail=availability=available os=27.0.0 platform=iOS
PROBE-RESULT name=fm.capabilities value=vision=true toolCalling=true guidedGeneration=true reasoning=false detail=availability=available os=27.0.0 platform=iOS
PROBE-RESULT name=fm.anyOf-enum-enforcement value=runs=10 violations=0 errors=0 detail=violatingValues=[] os=27.0.0 platform=iOS
PROBE-RESULT name=fm.attachment-label-recording value=unlabeledTokens=error(FoundationModels.LanguageModelError:-1) labeledTokens=error(FoundationModels.LanguageModelError:-1) unlabeledRespond=ok segments=[text,attachment(label:nil)] labeledRespond=ok segments=[text,attachment(label:probe-img)] unlabeledTool=timeout toolRan=true labeledTool=timeout toolRan=true detail=os=27.0.0 platform=iOS
PROBE-RESULT name=fm.collect-after-iteration value=collect-succeeded detail=iterations=12 contentChars=51 os=27.0.0 platform=iOS
PROBE-RESULT name=fm.concurrent-session-limit value=n=8 detail=0=ok 1=ok 2=ok 3=ok 4=ok 5=ok 6=ok 7=ok os=27.0.0 platform=iOS
PROBE-RESULT name=fm.image-token-cost value=none=6 128px=error(FoundationModels.LanguageModelError:-1) 256px=error(FoundationModels.LanguageModelError:-1) 512px=error(FoundationModels.LanguageModelError:-1) 896px=error(FoundationModels.LanguageModelError:-1) 1024px=error(FoundationModels.LanguageModelError:-1) 1792px=error(FoundationModels.LanguageModelError:-1) detail=os=27.0.0 platform=iOS
PROBE-RESULT name=fm.onToolCall-throw-effect value=respond-threw(ToolCallError) detail=toolRan=false entries=[instructions] os=27.0.0 platform=iOS
PROBE-RESULT name=fm.required-mode-no-tools value=threw detail=type=LanguageModelError domain=FoundationModels.LanguageModelError code=6 casts=[LanguageModelError] fmcase=unsupportedGenerationGuide desc=UnsupportedGuide os=27.0.0 platform=iOS
PROBE-RESULT name=fm.stream-zero-partials-tool-turn value=iteration-threw detail=type=LanguageModelError domain=FoundationModels.LanguageModelError code=0 casts=[LanguageModelError] fmcase=contextSizeExceeded(contextSize:4096,tokenCount:4099) toolRan=true os=27.0.0 platform=iOS
PROBE-RESULT name=fm.toolCallingMode-precedence value=profileRequired+optionsDisallowed=[toolCalled=false toolRan=false] profileDisallowed+optionsRequired=[threw LanguageModelError.contextSizeExceeded(contextSize:4096,tokenCount:4099)] detail=os=27.0.0 platform=iOS
PROBE-RESULT name=fm.transcript-policy-nil-default value=initialProperty=nil detail=nil=[threw(ToolCallError) toolRan=true entries=[instructions]] revert=[threw(ToolCallError) toolRan=true entries=[instructions]] preserve=[threw(ToolCallError) toolRan=true entries=[instructions,prompt,toolCalls]] os=27.0.0 platform=iOS
PROBE-RESULT name=fm.unsupportedLanguageOrLocale-error value=supportedCount=24 currentSupported=true probeLocale=am_ET respond=threw detail=LanguageModelError.guardrailViolation os=27.0.0 platform=iOS
PROBE-RESULT name=fm.spotlight-tool-surface value=name=spotlight_search includesSchema=true schemaCharacters=83570 artifact=spotlight-tool-schema-device-os27.0.0-24A5408d-xcode-27A5237l.txt artifactWrite=not-requested detail=Version 27.0 (Build 24A5408d) os=27.0.0 platform=iOS
PROBE-RESULT name=fm.spotlight-direct-call value=donation=ok naive=rejected-code-100 schema=rejected-code-100 ordered=rejected-code-100 replies=3 detail=cleanup=ok os=27.0.0 platform=iOS
PROBE-RESULT name=coreai.deviceArchitectureName value=h16p detail=hw.model=D83AP os=27.0.0 platform=iOS
PROBE-RESULT name=coreai.ndarray-zero-init value=all-zero-inconclusive detail=rounds=6 roundsWithGarbage=0 nonzeroBytesTotal=0 os=27.0.0 platform=iOS
PROBE-RESULT name=coreai.specializationOptions-defaults value=default.expectFrequentReshapes=false detail=default.allowed=[gpu,cpu,neuralEngine] default.preferred=nil cpuOnly.allowed=[cpu] cpuOnly.expectFrequentReshapes=false availableKinds=[cpu,neuralEngine,gpu] os=27.0.0 platform=iOS
PROBE-RESULT name=coreai.cache-delete-while-referenced value=live=threw(AIModelCacheError: failedToPurge("Deletion could not be completed, assets still in use")) detail=findableAfterLiveDelete=non-nil afterRelease=succeeded os=27.0.0 platform=iOS
PROBE-RESULT name=coreai.cache-location-size value=cachesGrowth=24576 appSupportGrowth=0 detail=sourceAsset=12288B specializeTook=0.0s newCacheEntries=["coreai-cache"] os=27.0.0 platform=iOS
PROBE-RESULT name=coreai.specialize-cancellation value=completed detail=elapsed=10.0s cacheAfter=entry-present os=27.0.0 platform=iOS
PROBE-RESULT name=coreai.specialize-return-identity value=same-entry detail=returnedBookmarkBytes=181 lookedUpBookmarkBytes=181 os=27.0.0 platform=iOS
PROBE-RESULT name=speech.assetInventory-status-order value=sorted=[unsupported,downloading,supported,installed] detail=pairs=[unsupported<downloading=true,downloading<supported=true,supported<installed=true] os=27.0.0 platform=iOS
```

Interpretation boundaries:

- `AIModelCacheError` is the runtime's dynamic name, not a public type in the captured Swift
  interface; use a generic `catch`.
- `24576 / 12288` is not a general 2× storage rule. It is the smallest measured default-cache
  footprint for this fixture and filesystem state.
- The cancellation probe did **not** establish cancellation semantics: specialization finished
  before the cancellation request could interrupt useful work. Repeat with a model whose
  specialization remains in flight.
- The bookmark result closes the default-cache composition only. An app-group cache still needs a
  signed, entitled target.

## Results harvested 2026-07-31 (verbatim probe output, both runs)

Fold these into the cited guide sections; the sim rows are the iOS 27.0 Simulator
(24A5390f) on the macOS 26.5.2 host, Apple Intelligence **disabled** on the host.

**Framework/environment findings (not single-gap results):**

- **Foundation Models works in the iOS 27.0 Simulator on a macOS 26.5 host** — and not
  just availability: text inference, guided generation and streaming all executed
  (`fm.availability value=available`; 10 guided-generation runs; 8 concurrent sessions all
  `ok`). This is with the HOST's Apple Intelligence toggle OFF (`swift test` on the host
  itself reports `.appleIntelligenceNotEnabled`) — so the 27.0 sim runtime resolves model
  assets independently of the host toggle. What is *missing* in the sim: tool-calling
  assets (`ModelManagerError 1026` / `UnifiedAssetFramework 5000`, "no underlying assets …
  com.apple.modelcatalog") and image attachments (`LanguageModelError -1`). Guides 5.1
  §13.4 and 17.2's "the Simulator punches out to the host" both need this nuance.
- **Core AI cannot target the Simulator in this beta**: `CoreAI.framework` and all six
  SubFrameworks exist in `iPhoneOS27.0.sdk` and are ABSENT from `iPhoneSimulator27.0.sdk`
  (`canImport(CoreAI)` is false there — the probe file is compile-excluded). Guide 7.1
  front matter should say so.
- **Evaluations runs offline**: `Evaluation.run(info:)` works programmatically under
  XCTest with canned subjects, no model, on the sim. Also: an evaluation whose
  `aggregateMetrics(using:)` registers nothing yields an **empty summary DataFrame and
  `aggregateValue` returns `-1.0` for every metric** — `-1.0` is the universal "no value"
  sentinel (6.1 §12 material).

**Per-gap results:**

```
PROBE-RESULT name=fm.tool-schema-flag-default value=true                             (26.5 host AND 27.0 sim)
PROBE-RESULT name=fm.tool-derived-name value=instance=FetchWeatherReportTool definition=FetchWeatherReportTool
PROBE-RESULT name=fm.contextSize value=4096                                          (26.5/MAC-27 host and DEVICE-27); app-hosted SIM-27=0 on 2026-09-04; tool-hosted SIM-27 changed from 4096 on 2026-08-17 to 0 on 2026-09-05
PROBE-RESULT name=fm.availability value=available                                    (27.0 sim; 26.5 host: unavailable(.appleIntelligenceNotEnabled))
PROBE-RESULT name=fm.includeSchemaInPrompt-recording value=legacyFalse=[ContextOptions(includeSchemaInPrompt: Optional(false), …)] contextOptionsFalse=[…Optional(false)…] default=[…Optional(true)…]
PROBE-RESULT name=fm.error-domain-context-overflow value=threw detail=type=LanguageModelError domain=FoundationModels.LanguageModelError code=0 casts=[LanguageModelError] desc=Content contains 168918 tokens, which exceeds the maximum allowed context size of 4096.
PROBE-RESULT name=fm.parsingError-thrown value=threw detail=type=ParsingError domain=FoundationModels.GeneratedContent.ParsingError code=1 casts=[GeneratedContent.ParsingError] desc=GeneratedContent does not contain a property 'summary'.
PROBE-RESULT name=fm.stream-early-break value=partialsSeen=2 entries=[prompt,response] isResponding=true followUp=not-attempted
PROBE-RESULT name=fm.collect-after-iteration value=collect-succeeded detail=iterations=13 contentChars=51
PROBE-RESULT name=fm.concurrent-session-limit value=n=8 detail=0=ok 1=ok 2=ok 3=ok 4=ok 5=ok 6=ok 7=ok
PROBE-RESULT name=fm.required-mode-no-tools value=threw detail=type=NSError domain=FoundationModels.LanguageModelError code=-1 casts=[] desc=…NSMultipleUnderlyingErrorsKey…
PROBE-RESULT name=fm.transcript-policy-nil-default value=initialProperty=nil detail=nil=[…entries=[instructions]] revert=[…entries=[instructions]] preserve=[…entries=[instructions,prompt]]
PROBE-RESULT name=fm.toolCallingMode-precedence value=profileRequired+optionsDisallowed=[toolCalled=false toolRan=false] profileDisallowed+optionsRequired=[threw …ModelManagerError 1026…]
PROBE-RESULT name=fm.onToolCall-throw-effect value=respond-threw(ModelManagerError) detail=toolRan=false entries=[instructions]
PROBE-RESULT name=fm.anyOf-enum-enforcement value=runs=10 violations=0 errors=0
PROBE-RESULT name=fm.guardrails-permissive-generable value=default=threw(LanguageModelError:2) permissive=threw(LanguageModelError:2)
PROBE-RESULT name=fm.image-token-cost value=none=6 128px=error(FoundationModels.LanguageModelError:-1) … 1792px=error(…:-1)
PROBE-RESULT name=eval.metric-identity value=summaryColumns=["Mean of Match"] detail=detailedColumns=["Input","Response","Expected","Match"] meanViaFreshInstance=0.5
PROBE-RESULT name=eval.mean-over-all-ignored value=-1.0 detail=detailedRows=4
PROBE-RESULT name=eval.subject-throws value=run-completed detail=samples=5 subjectFailures=2 detailedRows=5 meanMatch=1.0
PROBE-RESULT name=eval.disallowed-arguments-narrowing value=differentArgs(allPass=1.0) matchingArgs(allPass=0.0)
PROBE-RESULT name=eval.allowsAdditionalCalls-false value=control(allPass=1.0) withExtraCall(allPass=0.0) detail=controlPct=1.0 withExtraCallPct=0.5
PROBE-RESULT name=eval.generator-unreachable-target value=finished(produced=0) detail=sessionProviderInvocations=1 samples=1 invalidSamples=4   (run 1: invalidSamples=5)
```

Readings, one line each:

- **2.3 §4.4** — `includesSchemaInInstructions` default = `true` on both runtimes; only
  the "what does `false` tell the model" half of the GAP remains.
- **2.3 §2** — the derived `Tool.name` is the **verbatim type name** (no lowercasing, no
  snake_case, no suffix stripping) — so `SpotlightSearchTool`'s `spotlight_search` is
  hand-declared, not derived.
- **NEEDED item 7 / 3.1** — `contextSize` changed from 4096 on the 2026-08-17 tool-hosted
  Simulator run to 0 on 2026-09-05 despite the same recorded builds; the app-hosted Simulator
  also returned 0 on 2026-09-04. The device remained 4096, and the device overflow error text
  independently names 4096. The 8192 claim remains uncorroborated; keep reading the property at
  runtime and handle a zero result defensively.
- **17.1 §4.11** — the legacy `includeSchemaInPrompt:` parameter and
  `ContextOptions(includeSchemaInPrompt:)` are **one knob with two spellings**: both are
  recorded identically on `Transcript.Prompt.contextOptions`; the default records
  `Optional(true)`. The "mixing families" fear dissolves.
- **17.3 §4.4 / 17.1 ledger 9** — the framework **does throw
  `GeneratedContent.ParsingError`** (domain `FoundationModels.GeneratedContent.ParsingError`,
  code 1) when truncation yields an incomplete object; `rawContent` shows the partial JSON.
- **17.3 §6.3** — two table rows: context overflow throws a clean single-type
  `LanguageModelError` (code 0, casts only to itself); required-mode-no-tools throws the
  **generic `-1`** whose NSError domain says `FoundationModels.LanguageModelError` but
  which does **NOT cast to the Swift `LanguageModelError` type** (casts=[]) and wraps
  underlying errors via `NSMultipleUnderlyingErrorsKey` — the guide's "one value, two
  checks" concern is real for this failure mode.
- **17.3 §2.2 / 17.1 ledger 5** — `transcriptErrorHandlingPolicy` initial value is `nil`,
  and `nil`'s transcript outcome matches `.revertTranscript`, not `.preserveTranscript`
  (`preserve` retained the prompt entry; `nil` and `revert` rolled back to instructions).
- **2.2 ledger 8** — after an early `break`, a **partial `.response` entry is present** in
  the transcript and `isResponding` remains `true` ≥500 ms later — treat a broken-out
  session as still busy.
- **2.2 ledger 7** — `collect()` **after** full manual iteration succeeds and returns the
  complete response.
- **2.1 §8** — no concurrency ceiling observed at n=8 (sim; host-backed inference).
- **2.6 §7.4 / 17.1 §4.8** — suggestive, not final: profile `.required` + options
  `.disallowed` produced NO tool call, while profile `.disallowed` + options `.required`
  engaged the tool machinery (and hit the sim's missing-assets error) — both consistent
  with **per-call options winning**; confirm on MAC-27.
- **2.2 §4.6** — 10/10 greedy runs against a begged-for out-of-vocabulary answer produced
  only allowed `.anyOf` values (constrained-decoding reading; raise `PROBE_ENUM_RUNS` for N=100).
- **2.2 §11.3 ledger 13** — `.permissiveContentTransformations` did NOT change the outcome
  of a guardrail-blocked `@Generable` request (both threw `LanguageModelError` code 2) —
  supports "inert on the structured path" on this runtime.
- **6.1 §8.2** — `Metric` identity is **by name**: two evaluators emitting fresh
  `Metric("Match")` instances produce ONE detailed column and one `"Mean of Match"`
  summary column, and `aggregateValue(.mean(of: Metric("Match")))` through a fresh
  instance works (0.5 = both evaluators' values pooled — also note the pooling!).
- **6.1 §17.5** — mean over all-ignored = **`-1.0` sentinel** (not 0, not NaN, no trap);
  `#expect(mean >= threshold)` fails loudly, but `-1.0` is indistinguishable from
  "metric not registered", so assert scored-row counts too.
- **6.1 §17.7** — subject(from:) failures do **not** abort the run and the failed samples
  are **excluded from the aggregate** (mean over survivors = 1.0 with 2/5 failing) while
  still occupying detailed rows — the "silently improved score" hazard is CONFIRMED.
- **6.3 disallowed** — `disallowed` argument matchers **DO narrow** the prohibition
  (different-args call passes, matching-args call fails).
- **6.3 ledger** — `allowsAdditionalToolCalls: false` **is enforced**: an unexpected extra
  call fails `allPass` and halves `percentagePass`.
- **6.3 §3** — an unreachable `targetCount` does NOT throw and does NOT loop forever:
  `SampleGenerator` **finishes short after its internal retry budget** (`invalidSamples`
  4–5 across runs, matching `.random(retries: 5)`), `sessionProviderInvocations=1`;
  rejected samples ARE observable via `invalidSamples`.

## Results harvested 2026-07-31, second pass (probe-suite extension)

Same runtimes as above (26.5.2 host · iOS 27.0 sim 24A5390f). Verbatim lines, trimmed:

```
PROBE-RESULT name=speech.assetInventory-status-order value=sorted=[unsupported,supported,downloading,installed]   (HOST-26)
PROBE-RESULT name=speech.assetInventory-status-order value=sorted=[unsupported,downloading,supported,installed]   (SIM-27)
PROBE-RESULT name=fm.capabilities value=vision=true toolCalling=true guidedGeneration=true reasoning=false detail=availability=available   (SIM-27)
PROBE-RESULT name=fm.attachment-label-recording value=unlabeledTokens=error(FoundationModels.LanguageModelError:-1) labeledTokens=error(…:-1) unlabeledRespond=threw(-1) segments=[no-prompt-entry] labeledRespond=threw(-1) segments=[no-prompt-entry] unlabeledTool=threw(1026) toolRan=false labeledTool=threw(1026) toolRan=false
PROBE-RESULT name=fm.stream-zero-partials-tool-turn value=iteration-threw detail=type=ModelManagerError domain=ModelManagerServices.ModelManagerError code=1026 … toolRan=false
PROBE-RESULT name=fm.unsupportedLanguageOrLocale-error value=supportedCount=23 currentSupported=true probeLocale=am_ET respond=succeeded content=እባክህ በአማርኛ መልስ ስጠኝ…
PROBE-RESULT name=fm.spotlight-tool-surface value=name=spotlight_search includesSchema=true schemaCharacters=83494 artifact=spotlight-tool-schema-simulator-os27.0.0-24A5390f-xcode-27A5228h.txt
PROBE-RESULT name=fm.spotlight-direct-call value=donation=ok naive=rejected-code-100 schema=rejected-code-100 ordered=rejected-code-100 replies=3 detail=…cleanup=ok…
```

Readings, one line each:

- **16.1 §5.2 / G2 / NEXT-BETA §7** — the `AssetInventory.Status` `Comparable` ordering
  **differs between OS generations** (`supported` and `downloading` swap), so `<` is the
  **synthesized declaration-order** conformance and any code persisting or comparing
  `Status` order across OS versions is version-dependent. Both generations measured; the
  G2 gap closes with the sharpest possible answer.
- **5.1 §13.4** — `SystemLanguageModel.capabilities` on the sim claims `.vision` and
  `.toolCalling` while both fail at runtime with missing-asset errors → capabilities are
  a **static declaration**, not a per-destination health check; the `-1` ambiguity cannot
  be resolved by reading them. (`reasoning=false` is the one honest per-model bit.)
- **17.3 §6.3** — prompting in a locale `supportsLocale(_:)` rejects (`am_ET`) does
  **not** throw `.unsupportedLanguageOrLocale` on the sim — the model **silently
  answers** (echoing the prompt language). A silent-failure finding for 2.6's locale
  guidance: gate on `supportsLocale` yourself; the runtime will not stop you.
  `.rateLimited`/`.timeout`/`.refusal`/`.unsupportedTranscriptContent`/`.unsupportedGenerationGuide`
  remain deliberately unprobed (no clean trigger).
- **2.4 §7 / 2.3 §2** — `SpotlightSearchTool().name` **is** `spotlight_search` (declared,
  not derived — consistent with `fm.tool-derived-name`'s verbatim-type-name rule), and
  its `parameters` schema is a **full query DSL** (discriminated `search|schema|help|display`
  queries, `AllText`/`ContentType`/`Application` predicates, temporal models with
  variables, pipeline stages incl. `Compute`/`Count`/`Custom`, `x-order` annotations) —
  published nowhere. The complete 83,494-character value is committed as
  [`artifacts/spotlight-tool-schema-simulator-os27.0.0-24A5390f-xcode-27A5228h.txt`](artifacts/spotlight-tool-schema-simulator-os27.0.0-24A5390f-xcode-27A5228h.txt)
  (SHA-256 `4889148670380dc0907d86a9ac18fe1553fb3a35d55c466fee02a7b8749550d8`).
- **2.4 §7.1** — from the SIM-27 test-runner app container: `CSSearchableItem` donation
  **works** and `tool.searchResults` emits a `SearchReply` (stage token `search`) per
  call — the old "needs a signed app container" skip reason is refuted. But direct
  `call(arguments:)` could not be made to decode in this beta: the naive shape, the
  tool's own prescribed shape, and an order-preserving `init(properties:)` build were all
  rejected **in-band** (a code-100 JSON error inside the returned Prompt — the tool
  **never throws** on malformed arguments) with "Failed to parse generated content". Note
  the self-describing error is itself the documented recovery path Apple intends for the
  *model*. All three tested programmatic encodings were rejected on
  27A5228h/24A5390f; other encodings remain unproven. The collector observed three
  replies across the three calls, but the API exposes no correlation IDs, so that count
  does not establish a one-to-one call/reply mapping.
- **2.5 §6.4 / 2.3 / SILENT-FAILURES zero-partials** — both attachment-label and
  tool-turn-streaming probes are blocked on the sim (images `-1`, tool assets `1026`,
  identically for labeled and unlabeled) — fingerprints recorded; the real answers land
  on MAC-27/DEVICE-27.

## SKIPPED — gaps no automated probe can decide

| Gap | Guide § | Why skipped |
|---|---|---|
| `fm` CLI flag surface | 5.2 + NEEDED item 1 | CLI capture on a macOS 27 machine, not an XCTest |
| Instruments 27 lane names (FM + Core AI templates) | 5.1 §6.3 · 10.2 §3.2 + NEEDED item 3 | still human-read — but the workload + full GUI procedure now exist: `INSTRUMENTS-RECORDING.md` + `instruments.fm-workload` |
| Where a `#Playground` block executes | 5.1 §4 | Xcode UI behavior, not linkable API |
| Xcode "Simulated Apple Foundation Models Availability" menu contents | 5.1 §8 | Xcode UI |
| What a third-party `LanguageModel` populates in the FM instrument | 5.1 §10 | needs Instruments attached + human reading of lanes |
| ~~`SpotlightSearchTool` delegate invocation + attribute round-trip~~ | 2.4 §7 | **converted to measurements 2026-07-31** (`fm.spotlight-tool-surface` + `fm.spotlight-direct-call`): donation + replies work from the sim runner container; direct argument decode is the residue (in-band code-100 rejections) |
| `protectionClass` overload selection | 2.4 §7 | header question plus the app-container issue above |
| Apple-hosted adapter behavior after the 27 upgrade | 17.2 §3 | needs a preserved 26.x-built app with a working Apple-hosted adapter |
| Memory/thermal depth sweep for honest benchmarking | 15.2 | multi-hour thermal rig; out of scope for CI-shaped probes |
| Vision model image-typed inputs, both I/O paths | 17.5 §7 | needs a converted vision `.aimodel` artifact we do not have |
| Reading a palettized/sub-byte weight tensor via `view(as:)` | 17.5 §3 | needs a palettized compiled model artifact |
| `llm-benchmark` numbers for bring-your-own-model | 4.2 | external repo executable, not a package test |
| Skill-deactivation vs in-flight tool call race | 3.3 §16 | needs `apple/foundation-models-utilities` (external dependency) + model; this package is deliberately dependency-free |
| Whose quota an evaluation run spends | 6.3 §5 | unanswerable by probing — needs an Apple statement; probing burns a day's PCC quota without attributing the account |
| Synthetic-generation internal batch size | 6.3 §4 | not observable via any API; would need OS log scraping of private subsystems |
| App-group cache identity (`AIModelCache(appGroup:)`) | 7.2 §9 | needs a signed, entitled host app; the default-cache half **is** probed (`coreai.specialize-return-identity`) |
| Judge alignment quality / weighted kappa | 6.2 | human judgment of output quality |
| Full context-exhaustion observability during long generation | 6.3 §5 | needs an unbounded generation run; the bounded half (sessionProvider counting, `invalidSamples`) is folded into `eval.generator-unreachable-target` |

## Package layout

- `Package.swift` — swift-tools 6.2, platforms `.macOS(.v26)` / `.iOS(.v26)` (the `.v26`
  platform constants require the 6.2 manifest API).
- `Sources/ProbeSupport` — the `PROBE-RESULT` printer, env knobs, and deadline-safe
  timeout race shared by the XCTest and standalone workloads.
- `Tests/ProbesTests/FoundationModelsProbes.swift` — 22 FM probes (also home of the
  shared helpers, internal so the other probe files reuse them; `errorFingerprint`
  decodes the concrete `LanguageModelError` case + payload on 27 runtimes).
- `Tests/ProbesTests/CoreAIProbes.swift` — 7 Core AI probes, whole file
  `#if canImport(CoreAI)` (27-only module with no 26 API; also absent from the simulator
  SDK, so this file only exists in macOS/device builds).
- `Tests/ProbesTests/EvaluationsProbes.swift` — 6 Evaluations probes,
  `#if canImport(Evaluations)` (Xcode-bundled framework, `anyAppleOS 27.0`-gated;
  `Evaluation.run(info:)` makes five of the six offline-decidable — they already ran).
- `Tests/ProbesTests/SpeechProbes.swift` — the `AssetInventory.Status` ordering probe
  (runs on every destination, no skips).
- `Tests/ProbesTests/SpotlightProbes.swift` — the two `SpotlightSearchTool` probes
  (CoreSpotlight + FoundationModels imports activate the cross-import overlay).
- `Tests/ProbesTests/InstrumentsWorkloadProbes.swift` — the env-gated Instruments
  recording workload (never a `PROBE-RESULT`; narrates `WORKLOAD` lines).
- `Workload/fmworkload.swift` — standalone fallback recording target, deliberately
  OUTSIDE the package (bare `swiftc` compiles it together with
  `Sources/ProbeSupport/ProbeSupport.swift`, then `simctl spawn`; see
  `INSTRUMENTS-RECORDING.md`).
