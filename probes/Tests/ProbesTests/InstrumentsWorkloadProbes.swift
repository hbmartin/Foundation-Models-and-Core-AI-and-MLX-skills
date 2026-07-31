// InstrumentsWorkloadProbes — the RECORDING TARGET for the manual Instruments
// lane-name capture. Not a measuring probe: it produces no PROBE-RESULT lines.
//
// Destinations: SIM-27 (manual GUI session) · MAC-27 · DEVICE-27.
// Normal suite runs (no env knob) XCTSkip this test on every destination.

import Foundation
import FoundationModels
import ProbeSupport
import XCTest

final class InstrumentsWorkloadProbes: XCTestCase {

    // MARK: instruments.fm-workload  [SIM-27 (manual) · MAC-27 · DEVICE-27]
    //
    // GAP: guides/part-05-prototyping-profiling-non-swift/references/01-playground-and-
    //      instruments.md §6.3 (four of the six Foundation Models instrument lane names are
    //      unknown — they stream from the recording target at attach time and are not on
    //      disk) + notes/NEEDED-FROM-A-MACOS-27-MACHINE.md item 3. Headless
    //      `xcrun xctrace record` hangs against the booted sim for every template on this
    //      26.5 host (measured 2026-07-31), so a human must attach the Instruments GUI to a
    //      live process — this test IS that process. Full procedure:
    //      probes/INSTRUMENTS-RECORDING.md.
    //
    // Workload design (what each phase lights up on the timeline):
    //      PHASE 1 prefill-heavy — ~1,500-word varied prompt, 8-token answer
    //              (Model Inference lane: long YELLOW/input segment)
    //      PHASE 2 decode-heavy — short prompt, ~400-token streamed answer
    //              (Model Inference lane: long ORANGE/generation segment)
    //      PHASE 3 second session with a DIFFERENT instructions string
    //              (Instructions lane: a second region — one region per
    //              instruction-set+toolset)
    //      PHASE 4 error markers — the proven guardrail-trip and context-overflow prompts,
    //              caught and narrated (whether any lane renders error badges)
    //      Loops until PROBE_WORKLOAD_SECONDS elapses. Stdout narration is prefixed
    //      "WORKLOAD " (never PROBE-RESULT) with wall-clock offsets so the human can
    //      correlate timeline regions against phases.
    //
    // Knobs: PROBE_INSTRUMENTS_WORKLOAD=1 (required to run at all),
    //        PROBE_WORKLOAD_SECONDS (default 300),
    //        PROBE_WORKLOAD_ATTACH_SECONDS (default 20 — countdown before inference starts,
    //        the window in which to pick the process in Instruments).
    // Write-back: none directly — the human transcription (six lane header strings,
    //        detail-pane columns, region counts) is the artifact; its destinations are
    //        enumerated in INSTRUMENTS-RECORDING.md.
    func testInstrumentsRecordingWorkload() async throws {
        guard Probe.env("PROBE_INSTRUMENTS_WORKLOAD") == "1" else {
            throw XCTSkip("SKIPPED: set PROBE_INSTRUMENTS_WORKLOAD=1 (see probes/INSTRUMENTS-RECORDING.md)")
        }
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        let totalSeconds = Double(Probe.env("PROBE_WORKLOAD_SECONDS") ?? "300") ?? 300
        let attachSeconds = Int(Probe.env("PROBE_WORKLOAD_ATTACH_SECONDS") ?? "20") ?? 20
        let start = Date()

        func narrate(_ message: String) {
            print("WORKLOAD t+\(String(format: "%.1f", Date().timeIntervalSince(start)))s \(message)")
            fflush(stdout)
        }

        let info = ProcessInfo.processInfo
        narrate("attach-target process=\(info.processName) pid=\(info.processIdentifier) \(Probe.runtimeDescription)")
        for t in stride(from: attachSeconds, through: 1, by: -1) {
            narrate("attach-window t-\(t)s — pick this process in Instruments and press Record")
            try? await Task.sleep(for: .seconds(1))
        }

        let instructionsA = "You are a terse inventory summarizer. Answer in one word."
        let instructionsB = "You are a pirate poet. Answer only in rhyme, four lines maximum."
        // Varied filler — a single repeated token trips the guardrails before anything
        // interesting happens (measured; see fm.error-domain-context-overflow).
        let words = ["harbor", "lantern", "copper", "meadow", "quartz", "violet", "ember",
                     "willow", "granite", "saffron", "cedar", "marble", "falcon", "amber",
                     "juniper", "basalt", "orchid", "raven", "thistle", "cobalt"]
        let filler = (0..<1_500).map { words[$0 % words.count] + String($0) }.joined(separator: " ")
        let guardrailPrompt = """
        Tag this book review: "A brutal, blood-soaked revenge saga — the duel scenes are \
        graphically violent, limbs are severed, and the villain is flayed alive in the finale. \
        Still, the prose is gorgeous."
        """

        var round = 0
        while Date().timeIntervalSince(start) < totalSeconds {
            round += 1
            // PHASE 1 — prefill-heavy: long prompt, tiny answer.
            do {
                narrate("phase=1-prefill round=\(round) event=start")
                let session = LanguageModelSession(instructions: instructionsA)
                _ = try await Probe.withTimeout(seconds: 180) {
                    try await session.respond(
                        to: "Summarize this inventory in one word: \(filler)",
                        options: GenerationOptions(samplingMode: .greedy, maximumResponseTokens: 8))
                }
                narrate("phase=1-prefill round=\(round) event=end")
            } catch {
                narrate("phase=1-prefill round=\(round) event=error \(errorFingerprint(error))")
            }
            // PHASE 2 — decode-heavy: short prompt, long streamed answer (fresh session,
            // SAME instructions string, so the Instructions-lane region continues).
            do {
                narrate("phase=2-decode round=\(round) event=start")
                let session = LanguageModelSession(instructions: instructionsA)
                let partials = try await Probe.withTimeout(seconds: 180) { () -> Int in
                    var n = 0
                    let stream = session.streamResponse(
                        to: "Write twelve short sentences about tide pools.",
                        options: GenerationOptions(maximumResponseTokens: 400))
                    for try await _ in stream { n += 1 }
                    return n
                }
                narrate("phase=2-decode round=\(round) event=end partials=\(partials.map(String.init) ?? "timeout")")
            } catch {
                narrate("phase=2-decode round=\(round) event=error \(errorFingerprint(error))")
            }
            // PHASE 3 — instructions switch: a session with a DIFFERENT instruction set.
            do {
                narrate("phase=3-switch round=\(round) event=start (second Instructions-lane region)")
                let session = LanguageModelSession(instructions: instructionsB)
                _ = try await Probe.withTimeout(seconds: 120) {
                    try await session.respond(
                        to: "Describe the sea.",
                        options: GenerationOptions(maximumResponseTokens: 80))
                }
                narrate("phase=3-switch round=\(round) event=end")
            } catch {
                narrate("phase=3-switch round=\(round) event=error \(errorFingerprint(error))")
            }
            // PHASE 4 — error markers: guardrail trip, then context overflow.
            do {
                narrate("phase=4a-guardrail round=\(round) event=start")
                let session = LanguageModelSession()
                _ = try await Probe.withTimeout(seconds: 120) {
                    try await session.respond(
                        to: guardrailPrompt,
                        options: GenerationOptions(samplingMode: .greedy, maximumResponseTokens: 60))
                }
                narrate("phase=4a-guardrail round=\(round) event=no-error")
            } catch {
                narrate("phase=4a-guardrail round=\(round) event=threw code=\((error as NSError).code)")
            }
            do {
                narrate("phase=4b-overflow round=\(round) event=start")
                let session = LanguageModelSession()
                let huge = "Summarize this inventory list: " + (0..<30_000).map { "item\($0)" }.joined(separator: " ")
                _ = try await Probe.withTimeout(seconds: 120) {
                    try await session.respond(
                        to: huge,
                        options: GenerationOptions(maximumResponseTokens: 16))
                }
                narrate("phase=4b-overflow round=\(round) event=no-error")
            } catch {
                narrate("phase=4b-overflow round=\(round) event=threw code=\((error as NSError).code)")
            }
            narrate("round=\(round) complete")
        }
        narrate("done rounds=\(round)")
    }
}
