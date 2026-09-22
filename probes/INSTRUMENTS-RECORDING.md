# Instruments 27 UI capture — the one manual GUI session

**Goal.** Confirm the documented lane order and capture the detail-pane columns, labels, colors,
and error badges of the **Foundation Models** template; transcribe the still-unknown lane and metric
names of the **Core AI** template. This is the last original evidence gap on this machine that needs
no new hardware (`notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 3): rendered instrument details
**stream from the recording target at attach time** — they are not on disk — and headless `xcrun
xctrace record` against the booted simulator **hangs for every template on this 26.5 host** (measured
2026-07-31; `--no-prompt` set, `.trace` frozen at 52 KB). So: a human, the Instruments GUI, and a live
Foundation Models workload.

The workload is `InstrumentsWorkloadProbes.testInstrumentsRecordingWorkload` — an
env-gated XCTest that loops four narrated phases designed to light up the known lanes
(prefill-heavy → decode-heavy → an instructions switch → two deliberate errors). Only
all six FM lane names are now documented by Apple — *Session, Request, Instructions, Model
Inference, Tool,* and *Model Loading* — so the session below verifies their rendered order and
captures UI details the written page does not enumerate.

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

3. Start the workload (10-minute budget; the countdown gives you ~20 s to attach). The canonical
   runner uses the tool-hosted `Probes-Package` simulator scheme, injects the prefixed variables
   into the generated `.xctestrun`, and keeps the logs and `.xcresult` in a clean artifact
   directory:

   ```bash
   export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
   PROBE_INSTRUMENTS_WORKLOAD=1 \
   PROBE_WORKLOAD_SECONDS=600 \
   PROBE_WORKLOAD_ATTACH_SECONDS=20 \
     ./scripts/run-probes.sh simulator -- \
       -only-testing:ProbesTests/InstrumentsWorkloadProbes/testInstrumentsRecordingWorkload
   ```
   The console prints a banner:
   `WORKLOAD … attach-target process=<name> pid=<pid> …` followed by a countdown.
   **The printed pid is the authoritative selector** — the runner may appear under a
   generic name in the target list.
   If attaching to the XCTest runner itself misbehaves, use the standalone workload below with
   `SIMCTL_CHILD_` variables; that fallback was exercised against 27A5228h.
4. In Instruments: **File ▸ New… ▸ Foundation Models** template → in the target chooser
   pick the **iPhone 17 Pro (27.0) simulator device**, then the running process from
   step 3's banner → **Record**. Click through the privacy consent (guide 5.1 §5.2 —
   the FM instrument captures prompt/response text for the duration of the trace).
5. Record **at least two full loop rounds** (~3 minutes — the console narrates
   `WORKLOAD … round=N complete`), then Stop. The workload keeps looping; kill it with
   Ctrl-C when done, or let the 600 s budget expire.

### What to transcribe (this is the deliverable)

- Confirm the six documented lane headers of the `com.apple.FoundationModels` instrument,
  top-to-bottom and **verbatim** — including capitalization — and record any mismatch.
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
SIMCTL_CHILD_PROBE_INSTRUMENTS_WORKLOAD=1 \
  xcrun simctl spawn booted ./fmworkload
```

`PROBE_INSTRUMENTS_WORKLOAD=1` is explicit consent to read the host-backed default model. Attach
Instruments to the `fmworkload` process; same transcription list. The 2026-08-01 smoke run
on the iOS 27 simulator resolved the model as available and confirmed that the workload window
starts only after the attach countdown, then stops without starting another phase after its
deadline. Recheck the printed availability line on later runtimes.

## Where the transcription gets written back

1. `guides/part-05-prototyping-profiling-non-swift/references/01-playground-and-instruments.md`
   §6.3 — confirm or correct the documented lane order and add measured detail-pane columns,
   labels, colors, and error badges. Citation line: *"measured, Instruments 27.0 beta (27A5228h)
   GUI against the iOS 27.0 simulator (24A5390f), 2026-MM-DD"*.
2. `guides/part-10-coreai-hardware-authoring-debugging/references/02-debugging-and-profiling.md`
   §3 — the Core AI template's lane/metric/column names (names only; live Core AI events
   remain a DEVICE-27 item).
3. `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 3 → ✅ RESOLVED, with method + date, once both
   the Foundation Models UI details and Core AI names have been captured.
4. `probes/README.md` — flip the two Instruments rows in the SKIPPED table to answered,
   pointing here.
