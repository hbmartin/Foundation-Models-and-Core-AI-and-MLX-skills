// fmworkload — standalone Instruments recording target for the iOS 27 simulator
// (fallback Option A; the primary target is the env-gated XCTest workload in
// ../Tests/ProbesTests/InstrumentsWorkloadProbes.swift — see
// probes/INSTRUMENTS-RECORDING.md for both procedures).
//
// This file lives OUTSIDE the SwiftPM package on purpose: it is compiled with a
// bare swiftc against the iOS-simulator SDK and spawned into the booted sim,
// so it cannot link ProbeSupport and duplicates the two tiny helpers it needs.
//
// Build & run (-parse-as-library because a bare single-file swiftc otherwise
// treats the file as top-level code, which conflicts with @main):
//   cd probes/Workload
//   xcrun -sdk iphonesimulator swiftc -target arm64-apple-ios27.0-simulator \
//       -parse-as-library -O fmworkload.swift -o fmworkload
//   xcrun simctl spawn booted ./fmworkload
//
// The first run doubles as a probe: whether Foundation Models resolves model
// assets in a bare spawned process (no app container) is unmeasured. If the
// banner is followed by availability=unavailable or a -1 fingerprint, paste
// that output into probes/README.md as the finding and use the primary
// (XCTest-hosted) procedure instead.

import Foundation
import FoundationModels

@main
struct FMWorkload {
    static let workloadStart = Date()

    static func narrate(_ message: String) {
        print("WORKLOAD t+\(String(format: "%.1f", Date().timeIntervalSince(workloadStart)))s \(message)")
        fflush(stdout)
    }

    static func withTimeout<T: Sendable>(
        seconds: Double,
        _ op: @escaping @Sendable () async throws -> T
    ) async throws -> T? {
        try await withThrowingTaskGroup(of: T?.self) { group in
            group.addTask { try await op() }
            group.addTask {
                try? await Task.sleep(for: .seconds(seconds))
                return nil
            }
            let first = try await group.next() ?? nil
            group.cancelAll()
            return first
        }
    }

    static func fingerprint(_ error: any Error) -> String {
        let ns = error as NSError
        return "type=\(type(of: error)) domain=\(ns.domain) code=\(ns.code) desc=\(String(describing: error).prefix(200))"
    }

    static func main() async {
        let env = ProcessInfo.processInfo.environment
        let totalSeconds = Double(env["PROBE_WORKLOAD_SECONDS"] ?? "300") ?? 300
        let attachSeconds = Int(env["PROBE_WORKLOAD_ATTACH_SECONDS"] ?? "20") ?? 20

        let info = ProcessInfo.processInfo
        narrate("attach-target process=\(info.processName) pid=\(info.processIdentifier)")
        let model = SystemLanguageModel.default
        narrate("availability=\(model.isAvailable ? "available" : "unavailable") detail=\(String(describing: model.availability))")
        guard model.isAvailable else {
            narrate("bare-spawned-process finding: model UNAVAILABLE — record this in probes/README.md and use the XCTest-hosted workload instead")
            return
        }
        for t in stride(from: attachSeconds, through: 1, by: -1) {
            narrate("attach-window t-\(t)s — pick this process in Instruments and press Record")
            try? await Task.sleep(for: .seconds(1))
        }

        let instructionsA = "You are a terse inventory summarizer. Answer in one word."
        let instructionsB = "You are a pirate poet. Answer only in rhyme, four lines maximum."
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
        while Date().timeIntervalSince(workloadStart) < totalSeconds {
            round += 1
            do {
                narrate("phase=1-prefill round=\(round) event=start")
                let session = LanguageModelSession(instructions: instructionsA)
                _ = try await withTimeout(seconds: 180) {
                    try await session.respond(
                        to: "Summarize this inventory in one word: \(filler)",
                        options: GenerationOptions(samplingMode: .greedy, maximumResponseTokens: 8))
                }
                narrate("phase=1-prefill round=\(round) event=end")
            } catch {
                narrate("phase=1-prefill round=\(round) event=error \(fingerprint(error))")
            }
            do {
                narrate("phase=2-decode round=\(round) event=start")
                let session = LanguageModelSession(instructions: instructionsA)
                let partials = try await withTimeout(seconds: 180) { () -> Int in
                    var n = 0
                    let stream = session.streamResponse(
                        to: "Write twelve short sentences about tide pools.",
                        options: GenerationOptions(maximumResponseTokens: 400))
                    for try await _ in stream { n += 1 }
                    return n
                }
                narrate("phase=2-decode round=\(round) event=end partials=\(partials.map(String.init) ?? "timeout")")
            } catch {
                narrate("phase=2-decode round=\(round) event=error \(fingerprint(error))")
            }
            do {
                narrate("phase=3-switch round=\(round) event=start (second Instructions-lane region)")
                let session = LanguageModelSession(instructions: instructionsB)
                _ = try await withTimeout(seconds: 120) {
                    try await session.respond(
                        to: "Describe the sea.",
                        options: GenerationOptions(maximumResponseTokens: 80))
                }
                narrate("phase=3-switch round=\(round) event=end")
            } catch {
                narrate("phase=3-switch round=\(round) event=error \(fingerprint(error))")
            }
            do {
                narrate("phase=4a-guardrail round=\(round) event=start")
                let session = LanguageModelSession()
                _ = try await withTimeout(seconds: 120) {
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
                _ = try await withTimeout(seconds: 120) {
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
