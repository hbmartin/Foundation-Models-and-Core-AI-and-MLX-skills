# Instruments 27 lane-name capture — the one manual GUI session

**Goal.** Transcribe the lane names (and detail-pane columns) of the **Foundation Models**
and **Core AI** Instruments templates. This is the last evidence gap on this machine that
needs no new hardware (`notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 3): the lane
definitions **stream from the recording target at attach time** — they are not on disk —
and headless `xcrun xctrace record` against the booted simulator **hangs for every
template on this 26.5 host** (measured 2026-07-31; `--no-prompt` set, `.trace` frozen at
52 KB). So: a human, the Instruments GUI, and a live Foundation Models workload.

The workload is `InstrumentsWorkloadProbes.testInstrumentsRecordingWorkload` — an
env-gated XCTest that loops four narrated phases designed to light up the known lanes
(prefill-heavy → decode-heavy → an instructions switch → two deliberate errors). Only
two of the six FM lane names are known from Apple's corpus (*Instructions*, *Model
Inference*); the session below reads the other four off the timeline.

---

## Preparation

1. Boot the simulator and wait for it to finish booting:
   ```bash
   xcrun simctl boot "iPhone 17 Pro" 2>/dev/null; open -a Simulator
   ```
   (Create the device first with `xcrun simctl create` if it does not exist.)
2. Open the **beta** Instruments — the release Instruments has no 27 templates:
   ```bash
   open /Applications/Xcode-beta.app/Contents/Applications/Instruments.app
   ```
   Verify via Instruments ▸ About that this is the 27.0 build.

## Session 1 — Foundation Models template

3. Start the workload (10-minute budget; the countdown gives you ~20 s to attach):
   ```bash
   cd probes
   export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
   PROBE_INSTRUMENTS_WORKLOAD=1 PROBE_WORKLOAD_SECONDS=600 \
     xcodebuild test -scheme Probes-Package \
     -destination 'platform=iOS Simulator,OS=27.0,name=iPhone 17 Pro' \
     -only-testing:ProbesTests/InstrumentsWorkloadProbes/testInstrumentsRecordingWorkload
   ```
   The console prints a banner:
   `WORKLOAD … attach-target process=<name> pid=<pid> …` followed by a countdown.
   **The printed pid is the authoritative selector** — the runner may appear under a
   generic name in the target list.
   Shell-prefixed variables configure `xcodebuild` itself but are not guaranteed to enter the
   simulator test runner. Set these three variables in the scheme/test-plan environment when using
   XCTest. For a command-line-only run, use the standalone workload below with `SIMCTL_CHILD_`
   variables; that path was exercised against 27A5228h.
4. In Instruments: **File ▸ New… ▸ Foundation Models** template → in the target chooser
   pick the **iPhone 17 Pro (27.0) simulator device**, then the running process from
   step 3's banner → **Record**. Click through the privacy consent (guide 5.1 §5.2 —
   the FM instrument captures prompt/response text for the duration of the trace).
5. Record **at least two full loop rounds** (~3 minutes — the console narrates
   `WORKLOAD … round=N complete`), then Stop. The workload keeps looping; kill it with
   Ctrl-C when done, or let the 600 s budget expire.

### What to transcribe (this is the deliverable)

- **All six lane header strings** of the `com.apple.FoundationModels` instrument,
  top-to-bottom, **verbatim** — including capitalization.
- For each lane: click it and copy the **detail-pane column names** from the bottom pane.
- **Instructions lane:** the region count and each region's label. Expect **≥ 2 regions**
  (the workload alternates two instruction strings — phases 1/2 vs phase 3).
- **Model Inference lane:** confirm the yellow (input/prefill) segments align with
  `phase=1-prefill` narration timestamps and orange (generation/decode) with
  `phase=2-decode`. Note any colors beyond yellow/orange.
- Whether phase 4's narrated errors (`phase=4a-guardrail … event=threw`,
  `phase=4b-overflow … event=threw`) render **any badge/marker in any lane**.
- A screenshot of the full timeline → save as `notes/instruments-27-fm-lanes.png`.

## Session 2 — Core AI template (one-shot, no events expected)

Core AI events **cannot occur in a simulator** (`CoreAI.framework` is absent from the
simulator SDK), but the lane chrome renders from the template itself, which is what we
need. Same booted sim:

6. **File ▸ New… ▸ Core AI** template → target the booted simulator device (**All
   Processes** is fine) → Record ~10 s → Stop.
7. Transcribe per instrument — `com.apple.dt.instruments.coreai`, `com.apple.ane`,
   `metal-gpu`, `coresampler2`: lane names, metric names, and detail-pane columns.
   Screenshot → `notes/instruments-27-coreai-lanes.png`.

## Fallback — the standalone spawned executable (Option A)

If attaching to the XCTest runner misbehaves, use the self-contained workload binary:

```bash
cd probes/Workload
export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
xcrun -sdk iphonesimulator swiftc -target arm64-apple-ios27.0-simulator \
    -parse-as-library -O ../Sources/ProbeSupport/ProbeSupport.swift \
    fmworkload.swift -o fmworkload
SIMCTL_CHILD_PROBE_WORKLOAD_SECONDS=600 \
SIMCTL_CHILD_PROBE_WORKLOAD_ATTACH_SECONDS=20 \
  xcrun simctl spawn booted ./fmworkload
```

Attach Instruments to the `fmworkload` process; same transcription list. The 2026-08-01 smoke run
on the iOS 27 simulator resolved the model as available and confirmed that the workload window
starts only after the attach countdown, then stops without starting another phase after its
deadline. Recheck the printed availability line on later runtimes.

## Where the transcription gets written back

1. `guides/part-05-prototyping-profiling-non-swift/references/01-playground-and-instruments.md`
   §6.3 — replace the lane-names GAP box with the six verbatim lane names + detail-pane
   columns. Citation line: *"measured, Instruments 27.0 beta (27A5228h) GUI against the
   iOS 27.0 simulator (24A5390f), 2026-MM-DD"*. Re-check §8 and §10, which currently
   reason from only the two known lane names.
2. `guides/part-10-coreai-hardware-authoring-debugging/references/02-debugging-and-profiling.md`
   §3 — the Core AI template's lane/metric/column names (names only; live Core AI events
   remain a DEVICE-27 item).
3. `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 3 → ✅ RESOLVED, with method + date;
   update the header prose (the remaining machine-dependent items become 1 and 7).
4. `probes/README.md` — flip the two Instruments rows in the SKIPPED table to answered,
   pointing here.
