// FoundationModelsProbes — executable evidence for the open FoundationModels
// behavioral gaps in the guide series.
//
// Destinations (see probes/README.md):
//   HOST-26   runs on the authoring host today (macOS 26.5, `swift test`)
//   SIM-27    runs on the iOS 27.0 Simulator today (xcodebuild test)
//   MAC-27    needs a Mac running macOS 27 (upgrade day)
//   DEVICE-27 needs a physical device on iOS/macOS 27 with Apple Intelligence
//
// Probes never fake a pass/fail: measuring probes print PROBE-RESULT and pass;
// branch probes print which documented behavior actually happened.

import Foundation
import CoreGraphics
import FoundationModels
import ProbeSupport
import XCTest

// MARK: - Fixture tools

/// Minimal conformance — declares ONLY `description` + `call`, so `name` and
/// `includesSchemaInInstructions` come from the protocol's default implementations.
/// The deliberately multi-word, `Tool`-suffixed type name makes the derivation rule
/// readable from the output (type name? lowercased? snake_cased? suffix stripped?).
private struct FetchWeatherReportTool: Tool {
    let description = "Fetches a weather report for a city."
    @Generable
    struct Arguments {
        var city: String
    }
    func call(arguments: Arguments) async throws -> String { "sunny" }
}

/// A tool that records whether it ran and echoes its argument.
private struct EchoTool: Tool {
    let name = "echo"
    let description = "Echoes the given text back. Use this tool whenever asked."
    let counter: Probe.Counter
    @Generable
    struct Arguments {
        var text: String
    }
    func call(arguments: Arguments) async throws -> String {
        counter.increment()
        return arguments.text
    }
}

private struct AlwaysThrowingTool: Tool {
    struct Boom: Error {}
    let name = "lookup"
    let description = "Looks up a record. Use this tool whenever asked."
    let counter: Probe.Counter
    @Generable
    struct Arguments {
        var key: String
    }
    func call(arguments: Arguments) async throws -> String {
        counter.increment()
        throw Boom()
    }
}

// MARK: - Fixture @Generable types (macro cannot attach to function-local types)

@Generable
private struct TinyWord {
    var word: String
}

@Generable
private struct WideRecord {
    var title: String
    var summary: String
    var mood: String
}

@Generable
private struct BookTags {
    var genre: String
    var themes: [String]
}

// MARK: - Shared helpers

private func skipUnlessModelAvailable(file: StaticString = #filePath, line: UInt = #line) throws {
    let model = SystemLanguageModel.default
    guard model.isAvailable else {
        throw XCTSkip("SystemLanguageModel unavailable on this destination: \(model.availability)")
    }
}

private func entrySummary(_ transcript: Transcript) -> String {
    transcript.map { entry -> String in
        switch entry {
        case .instructions: return "instructions"
        case .prompt: return "prompt"
        case .toolCalls: return "toolCalls"
        case .toolOutput: return "toolOutput"
        case .response: return "response"
        default: return Mirror(reflecting: entry).children.first?.label ?? "other"
        }
    }.joined(separator: ",")
}

private func errorFingerprint(_ error: any Error) -> String {
    let ns = error as NSError
    var casts: [String] = []
    if error is LanguageModelSession.ToolCallError { casts.append("ToolCallError") }
    if #available(macOS 27.0, iOS 27.0, *) {
        if error is LanguageModelError { casts.append("LanguageModelError") }
        if error is GeneratedContent.ParsingError { casts.append("GeneratedContent.ParsingError") }
        if error is LanguageModelSession.Error { casts.append("LanguageModelSession.Error") }
    }
    return "type=\(type(of: error)) domain=\(ns.domain) code=\(ns.code) casts=[\(casts.joined(separator: "|"))] desc=\(String(describing: error).prefix(300))"
}

// MARK: - Probes

final class FoundationModelsProbes: XCTestCase {

    // MARK: fm.tool-schema-flag-default  [HOST-26 · SIM-27 · MAC-27]
    //
    // GAP: guides/part-02-foundation-models-everyday-api/references/03-tools-and-tool-calling.md §4.4
    //      and notes/NEEDED-FROM-A-MACOS-27-MACHINE.md item 5 (residue).
    // Question: the default *value* of `Tool.includesSchemaInInstructions` — the
    //      swiftinterface shows the requirement + a default impl but cannot print the body.
    // Candidates: (a) true — schema injected into instructions by default;
    //             (b) false — schema withheld unless opted in.
    // Write-back: replace "default value 🔴 GAP" in §4.4 and the §14 ledger row with the
    //      printed value, per OS version (run on 26.5 host AND a 27 runtime — the default
    //      could differ across releases).
    func testToolIncludesSchemaInInstructionsDefault() {
        let tool = FetchWeatherReportTool()
        Probe.result(
            "fm.tool-schema-flag-default",
            "\(tool.includesSchemaInInstructions)",
            detail: Probe.runtimeDescription
        )
    }

    // MARK: fm.tool-derived-name  [HOST-26 · SIM-27 · MAC-27]
    //
    // GAP: part-02 …/03-tools-and-tool-calling.md §2 ("the exact string the derived name
    //      produces") — resolvable by "a device dump of Transcript.ToolDefinition(tool:).name
    //      for a tool that omits it", which is exactly what this prints.
    // Candidates: (a) verbatim type name "FetchWeatherReportTool"; (b) lowercased;
    //             (c) snake_case "fetch_weather_report_tool"; (d) suffix-stripped variants.
    // Write-back: state the rule in §2 and delete the SpotlightSearchTool speculation.
    func testToolDerivedNameDefault() {
        let tool = FetchWeatherReportTool()
        let viaInstance = tool.name
        let viaDefinition = Transcript.ToolDefinition(tool: tool).name
        Probe.result(
            "fm.tool-derived-name",
            "instance=\(viaInstance) definition=\(viaDefinition)",
            detail: "type=FetchWeatherReportTool \(Probe.runtimeDescription)"
        )
    }

    // MARK: fm.contextSize  [HOST-26 · SIM-27 · DEVICE-27]
    //
    // GAP: notes/NEEDED-FROM-A-MACOS-27-MACHINE.md item 7 (second bullet); also
    //      part-03 …/01-context-window-and-kv-cache.md (TN3193's 4096 vs the community 8192
    //      claim). The 26.5 interface hardcodes `return 4096`; the 27.0 interface returns a
    //      dynamic `_contextSize` on OS 27+.
    // Candidates: (a) 4096 everywhere; (b) 8192 (or other) on 27 hardware; the value may
    //             also differ between a 27 Simulator (host-backed) and a 27 device.
    // Write-back: the printed number per destination, closing the "third-party 8192" claim.
    func testSystemLanguageModelContextSize() {
        let size = SystemLanguageModel.default.contextSize
        Probe.result("fm.contextSize", "\(size)", detail: Probe.runtimeDescription)
    }

    // MARK: fm.availability  [HOST-26 · SIM-27 · MAC-27 · DEVICE-27]
    //
    // GAP: part-05 …/01-playground-and-instruments.md §13.4 ("whether the Foundation Models
    //      template works against the Simulator at all") — the runtime half of that family:
    //      does the Simulator resolve a model at all on this host, and with which
    //      unavailable-reason if not? Also part-17 …/02-adapter-sunset.md ("the Simulator
    //      punches out to the host macOS").
    // Candidates: (a) .available (simulator punched through to a host model);
    //             (b) .unavailable(.appleIntelligenceNotEnabled | .deviceNotEligible |
    //                 .modelNotReady | other).
    // Write-back: record the sim-on-26.5-host result verbatim in 5.1 §13.4 as the
    //      measured baseline; re-run after the host moves to 27.
    func testSystemModelAvailability() {
        let model = SystemLanguageModel.default
        Probe.result(
            "fm.availability",
            model.isAvailable ? "available" : "unavailable",
            detail: "availability=\(String(describing: model.availability)) \(Probe.runtimeDescription)"
        )
    }

    // MARK: fm.toolCallingMode-precedence  [MAC-27 · DEVICE-27]
    //
    // GAP: part-02 …/06-availability-errors-and-guardrails.md §7.4 and
    //      part-17 …/01-what-changed-checklist.md §4.8 — `toolCallingMode` exists on both
    //      `GenerationOptions` and as a `DynamicProfile` modifier (same type, SDK-verified);
    //      which surface wins when both are set is stated nowhere.
    // Candidates: (a) per-call options win; (b) profile wins; (c) merge/other.
    // Method: profile says .required, per-call options say .disallowed (and the inverse on a
    //      fresh session); with greedy sampling, whether a toolCalls entry lands in the
    //      transcript tells you which surface the inference layer honored.
    // Write-back: one sentence in both guides naming the winner; delete the "safe default:
    //      don't mix" hedge or keep it with the measured reason.
    func testToolCallingModePrecedence() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        @Sendable func run(profileMode: GenerationOptions.ToolCallingMode,
                           optionsMode: GenerationOptions.ToolCallingMode) async -> String {
            let counter = Probe.Counter()
            let tool = EchoTool(counter: counter)
            let profile = LanguageModelSession.Profile {
                Instructions("You are a test assistant. When asked to echo, use the echo tool.")
                tool
            }
            .toolCallingMode(profileMode)
            let session = LanguageModelSession(profile: profile)
            do {
                _ = try await session.respond(
                    to: "Echo the word ping.",
                    options: GenerationOptions(samplingMode: .greedy,
                                               maximumResponseTokens: 200,
                                               toolCallingMode: optionsMode)
                )
                let called = session.transcript.contains {
                    if case .toolCalls = $0 { return true } else { return false }
                }
                return "toolCalled=\(called) toolRan=\(counter.count > 0)"
            } catch {
                return "threw \(errorFingerprint(error))"
            }
        }

        let a = await run(profileMode: .required, optionsMode: .disallowed)
        let b = await run(profileMode: .disallowed, optionsMode: .required)
        Probe.result(
            "fm.toolCallingMode-precedence",
            "profileRequired+optionsDisallowed=[\(a)] profileDisallowed+optionsRequired=[\(b)]",
            detail: Probe.runtimeDescription
        )
    }

    // MARK: fm.includeSchemaInPrompt-recording  [MAC-27 · DEVICE-27]
    //
    // GAP: part-17 …/01-what-changed-checklist.md §4.11 — the 26-era
    //      `includeSchemaInPrompt:` parameter family vs the 27-era
    //      `contextOptions: ContextOptions(includeSchemaInPrompt:)` family are separate
    //      overload sets; what a session records when you use each (and what the default
    //      records) is unverified.
    // Method: `Transcript.Prompt.contextOptions` is readable in 27 — after each call,
    //      print the ContextOptions the framework actually recorded on the prompt entry.
    //      If the legacy parameter writes through to the recorded ContextOptions, they are
    //      one knob with two spellings; if not, they are genuinely parallel systems.
    // Candidates: (a) legacy param recorded as contextOptions.includeSchemaInPrompt;
    //             (b) legacy param NOT reflected (nil/default recorded);
    //             (c) default records nil vs true.
    // Write-back: rewrite §4.11's "which setting wins" box with the recorded values.
    func testIncludeSchemaInPromptRecording() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        @Sendable func lastPromptContextOptions(_ session: LanguageModelSession) -> String {
            for entry in session.transcript.reversed() {
                if case .prompt(let p) = entry {
                    return String(describing: p.contextOptions)
                }
            }
            return "no-prompt-entry"
        }

        var results: [String] = []
        do { // legacy family, schema off
            let session = LanguageModelSession()
            _ = try? await session.respond(to: "One word for joy.", generating: TinyWord.self,
                                           includeSchemaInPrompt: false,
                                           options: GenerationOptions(samplingMode: .greedy, maximumResponseTokens: 50))
            results.append("legacyFalse=[\(lastPromptContextOptions(session))]")
        }
        do { // 27 family, schema off
            let session = LanguageModelSession()
            _ = try? await session.respond(to: "One word for joy.", generating: TinyWord.self,
                                           options: GenerationOptions(samplingMode: .greedy, maximumResponseTokens: 50),
                                           contextOptions: ContextOptions(includeSchemaInPrompt: false))
            results.append("contextOptionsFalse=[\(lastPromptContextOptions(session))]")
        }
        do { // default
            let session = LanguageModelSession()
            _ = try? await session.respond(to: "One word for joy.", generating: TinyWord.self,
                                           options: GenerationOptions(samplingMode: .greedy, maximumResponseTokens: 50))
            results.append("default=[\(lastPromptContextOptions(session))]")
        }
        Probe.result("fm.includeSchemaInPrompt-recording", results.joined(separator: " "),
                     detail: Probe.runtimeDescription)
    }

    // MARK: fm.error-domain-context-overflow  [MAC-27 · DEVICE-27]
    //
    // GAP: part-17 …/03-error-taxonomy-migration.md §6.3 — "can one thrown value satisfy two
    //      of these checks?" What would resolve it: printing type(of:) and the NSError domain
    //      for each failure mode. This probe produces the context-overflow row of that table.
    // Candidates: (a) LanguageModelError.contextSizeExceeded only; (b) an NSError-bridged
    //             value castable to several FM error types; (c) a legacy GenerationError.
    // Write-back: a row in §6.3's table: failure mode → concrete type, domain, code, casts.
    func testErrorTypeForContextOverflow() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        // Varied, neutral filler: a single repeated word trips the guardrails (measured
        // 2026-07-31 on the 27.0 sim: LanguageModelError code=2 "May contain unsafe
        // content") before the context limit is ever reached.
        let hugePrompt = "Summarize this inventory list: " + (0..<30_000).map { "item\($0)" }.joined(separator: " ")
        let session = LanguageModelSession()
        do {
            let outcome = try await Probe.withTimeout(seconds: 120) {
                try await session.respond(to: hugePrompt,
                                          options: GenerationOptions(maximumResponseTokens: 16))
            }
            Probe.result("fm.error-domain-context-overflow",
                         outcome == nil ? "timeout" : "no-error",
                         detail: "a 30k-word prompt did not throw — \(Probe.runtimeDescription)")
        } catch {
            Probe.result("fm.error-domain-context-overflow", "threw",
                         detail: "\(errorFingerprint(error)) \(Probe.runtimeDescription)")
        }
    }

    // MARK: fm.parsingError-thrown  [MAC-27 · DEVICE-27]
    //
    // GAP: part-17 …/03-error-taxonomy-migration.md §4.4 and …/01-what-changed-checklist.md
    //      ledger item 9 — whether the framework ever actually throws
    //      `GeneratedContent.ParsingError` for a guided-generation decode failure, or wraps
    //      it, or re-prompts internally. Trigger: truncation — a multi-field @Generable with
    //      maximumResponseTokens too small to complete the object.
    // Candidates: (a) GeneratedContent.ParsingError; (b) LanguageModelError case;
    //             (c) success/partial (framework recovered internally).
    // Write-back: §4.4's "what is thrown" sentence, with the trigger recipe.
    func testParsingErrorThrownOnTruncation() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        let session = LanguageModelSession()
        do {
            let response = try await session.respond(
                to: "Describe a rainy harbor town.",
                generating: WideRecord.self,
                options: GenerationOptions(samplingMode: .greedy, maximumResponseTokens: 8)
            )
            Probe.result("fm.parsingError-thrown", "no-error",
                         detail: "truncated request succeeded: \(String(describing: response.content).prefix(120)) \(Probe.runtimeDescription)")
        } catch {
            Probe.result("fm.parsingError-thrown", "threw",
                         detail: "\(errorFingerprint(error)) \(Probe.runtimeDescription)")
        }
    }

    // MARK: fm.stream-early-break  [HOST-26* · MAC-27 · DEVICE-27]  (*if host model available)
    //
    // GAP: part-02 …/02-guided-generation-and-streaming.md ledger item 8 — Swift cancellation
    //      semantics of a stream broken out of early, and whether a partial entry lands in
    //      `session.transcript`. Resolution named by the guide: "a device test reading
    //      session.transcript after an early break".
    // Candidates: (a) partial .response entry present; (b) prompt entry only, response
    //             rolled back; (c) session left isResponding/wedged.
    // Write-back: ledger item 8 and §9's cancellation discussion.
    func testStreamEarlyBreakTranscriptState() async throws {
        try skipUnlessModelAvailable()

        let session = LanguageModelSession()
        var partials = 0
        let stream = session.streamResponse(
            to: "Write six short sentences about tide pools.",
            options: GenerationOptions(maximumResponseTokens: 400)
        )
        do {
            for try await _ in stream {
                partials += 1
                if partials >= 2 { break }
            }
        } catch {
            Probe.result("fm.stream-early-break", "iteration-threw",
                         detail: errorFingerprint(error))
            return
        }
        // Give any rollback/append a beat to land.
        try? await Task.sleep(for: .milliseconds(500))
        let entries = entrySummary(session.transcript)
        let responding = session.isResponding
        var followUp = "not-attempted"
        if !responding {
            do {
                _ = try await Probe.withTimeout(seconds: 60) {
                    try await session.respond(to: "Say done.",
                                              options: GenerationOptions(maximumResponseTokens: 20))
                }
                followUp = "succeeded"
            } catch {
                followUp = "threw \(type(of: error))"
            }
        }
        Probe.result(
            "fm.stream-early-break",
            "partialsSeen=\(partials) entries=[\(entries)] isResponding=\(responding) followUp=\(followUp)",
            detail: Probe.runtimeDescription
        )
    }

    // MARK: fm.collect-after-iteration  [HOST-26* · MAC-27 · DEVICE-27]
    //
    // GAP: part-02 …/02-guided-generation-and-streaming.md ledger item 7 (§9.3) — whether
    //      `ResponseStream.collect()` may be called after manual iteration.
    // Candidates: (a) returns the full response; (b) throws; (c) returns empty/partial.
    // Write-back: ledger item 7, replacing "Apple's collect() doc page, or a device test".
    func testCollectAfterManualIteration() async throws {
        try skipUnlessModelAvailable()

        let session = LanguageModelSession()
        let stream = session.streamResponse(
            to: "Name three primary colors.",
            options: GenerationOptions(maximumResponseTokens: 60)
        )
        var iterations = 0
        do {
            for try await _ in stream { iterations += 1 }
        } catch {
            Probe.result("fm.collect-after-iteration", "iteration-threw",
                         detail: errorFingerprint(error))
            return
        }
        do {
            let response = try await stream.collect()
            Probe.result("fm.collect-after-iteration",
                         "collect-succeeded",
                         detail: "iterations=\(iterations) contentChars=\(String(describing: response.content).count) \(Probe.runtimeDescription)")
        } catch {
            Probe.result("fm.collect-after-iteration", "collect-threw",
                         detail: "iterations=\(iterations) \(errorFingerprint(error)) \(Probe.runtimeDescription)")
        }
    }

    // MARK: fm.image-token-cost  [MAC-27 · DEVICE-27]
    //
    // GAP: part-03 …/01-context-window-and-kv-cache.md §2.4 + §16 ledger ("Image token cost")
    //      — no published token cost per image; thread 838613's "896 px longest dimension"
    //      downsample is a developer inference. Resolution named by the guide:
    //      tokenCount(for:) on a Prompt with one attachment, at several resolutions.
    // Candidates: (a) cost scales with resolution; (b) flat above a downsample cap (~896);
    //             (c) flat always.
    // Write-back: a small table in §2.4 (resolution → tokens), and confirm/refute 896.
    func testImageAttachmentTokenCost() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        func solidImage(side: Int) -> CGImage? {
            let ctx = CGContext(data: nil, width: side, height: side, bitsPerComponent: 8,
                                bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
                                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
            ctx?.setFillColor(CGColor(red: 0.2, green: 0.5, blue: 0.8, alpha: 1))
            ctx?.fill(CGRect(x: 0, y: 0, width: side, height: side))
            return ctx?.makeImage()
        }

        let model = SystemLanguageModel.default
        var rows: [String] = []
        let baseline = try await model.tokenCount(for: Prompt("Describe the attached image."))
        rows.append("none=\(baseline)")
        for side in [128, 256, 512, 896, 1024, 1792] {
            guard let image = solidImage(side: side) else { continue }
            let prompt = Prompt {
                "Describe the attached image."
                Attachment(image)
            }
            do {
                let count = try await model.tokenCount(for: prompt)
                rows.append("\(side)px=\(count)")
            } catch {
                let ns = error as NSError
                rows.append("\(side)px=error(\(ns.domain):\(ns.code))")
            }
        }
        Probe.result("fm.image-token-cost", rows.joined(separator: " "),
                     detail: Probe.runtimeDescription)
    }

    // MARK: fm.concurrent-session-limit  [MAC-27 · DEVICE-27]
    //
    // GAP: part-02 …/01-sessions-and-prompting.md §8 — "how many concurrent sessions the OS
    //      actually allows": no number, no specific error case, no query API. Resolution
    //      named by the guide: N sessions issuing respond simultaneously, recording which
    //      throw and with what.
    // Candidates: (a) all N succeed (serialized); (b) some throw a specific error;
    //             (c) throttled/hung beyond a ceiling.
    // Write-back: the observed ceiling/behavior at N=8 in §8's GAP box.
    func testConcurrentSessionCeiling() async throws {
        try skipUnlessModelAvailable()

        let n = Int(Probe.env("PROBE_CONCURRENT_SESSIONS") ?? "8") ?? 8
        let outcomes = await withTaskGroup(of: (Int, String).self) { group -> [(Int, String)] in
            for i in 0..<n {
                group.addTask {
                    let session = LanguageModelSession()
                    do {
                        let r = try await Probe.withTimeout(seconds: 180) {
                            try await session.respond(
                                to: "Reply with the word ok.",
                                options: GenerationOptions(maximumResponseTokens: 10))
                        }
                        return (i, r == nil ? "timeout" : "ok")
                    } catch {
                        return (i, "threw(\(type(of: error)):\((error as NSError).code))")
                    }
                }
            }
            var all: [(Int, String)] = []
            for await o in group { all.append(o) }
            return all.sorted { $0.0 < $1.0 }
        }
        let summary = outcomes.map { "\($0.0)=\($0.1)" }.joined(separator: " ")
        Probe.result("fm.concurrent-session-limit", "n=\(n)", detail: "\(summary) \(Probe.runtimeDescription)")
    }

    // MARK: fm.onToolCall-throw-effect  [MAC-27 · DEVICE-27]
    //
    // GAP: part-03 …/04-agentic-orchestration.md §6 — a throw from the `onToolCall` profile
    //      callback: community says "the tool never runs, control returns to the loop"
    //      (per-call veto); Apple's wording says the error propagates to `respond`
    //      (turn-level abort). Which transcript state results is observable only on device.
    // Candidates: (a) tool skipped, respond completes; (b) respond throws, transcript rolled
    //             back; (c) respond throws, partial transcript preserved; (d) tool runs anyway.
    // Write-back: §6's veto-vs-abort paragraph, plus the transcript-state sentence.
    func testOnToolCallThrowEffect() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        struct Veto: Error {}
        let counter = Probe.Counter()
        let tool = EchoTool(counter: counter)
        let profile = LanguageModelSession.Profile {
            Instructions("You are a test assistant. When asked to echo, use the echo tool.")
            tool
        }
        .onToolCall { (_: Transcript.ToolCall) in throw Veto() }
        let session = LanguageModelSession(profile: profile)
        var outcome: String
        do {
            let r = try await Probe.withTimeout(seconds: 120) {
                try await session.respond(
                    to: "Echo the word ping.",
                    options: GenerationOptions(samplingMode: .greedy,
                                               maximumResponseTokens: 200,
                                               toolCallingMode: .required))
            }
            outcome = r == nil ? "timeout" : "respond-succeeded"
        } catch {
            outcome = "respond-threw(\(type(of: error)))"
        }
        Probe.result(
            "fm.onToolCall-throw-effect",
            outcome,
            detail: "toolRan=\(counter.count > 0) entries=[\(entrySummary(session.transcript))] \(Probe.runtimeDescription)"
        )
    }

    // MARK: fm.required-mode-no-tools  [MAC-27 · DEVICE-27]
    //
    // GAP: part-03 …/04-agentic-orchestration.md §6 and part-02 …/03-tools §? — the
    //      documented behavior of `.required` with an empty toolset is unknown; betas emit
    //      console-only "Tool Choice requires tools" wrapped in LanguageModelError -1
    //      (FB23643759). Needs a clean 27.0 GA device test.
    // Candidates: (a) a specific LanguageModelError case; (b) generic -1; (c) mode ignored,
    //             respond succeeds.
    // Write-back: the error taxonomy row + §6's GAP box; note whether the GA fixed FB23643759.
    func testRequiredToolCallingModeWithNoTools() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        let session = LanguageModelSession()
        do {
            let r = try await Probe.withTimeout(seconds: 120) {
                try await session.respond(
                    to: "Say hello.",
                    options: GenerationOptions(samplingMode: .greedy,
                                               maximumResponseTokens: 30,
                                               toolCallingMode: .required))
            }
            Probe.result("fm.required-mode-no-tools", r == nil ? "timeout" : "no-error",
                         detail: Probe.runtimeDescription)
        } catch {
            Probe.result("fm.required-mode-no-tools", "threw",
                         detail: "\(errorFingerprint(error)) \(Probe.runtimeDescription)")
        }
    }

    // MARK: fm.transcript-policy-nil-default  [MAC-27 · DEVICE-27]
    //
    // GAP: part-17 …/03-error-taxonomy-migration.md §2.2 and …/01-what-changed-checklist.md
    //      ledger item 5 — `transcriptErrorHandlingPolicy` is Optional; which behavior `nil`
    //      selects (.revertTranscript or .preserveTranscript) is unnamed by docs and
    //      inexpressible in a swiftinterface.
    // Method: force a mid-turn tool failure under nil / .revertTranscript /
    //      .preserveTranscript on fresh sessions; the transcript entry pattern under nil
    //      matches whichever explicit policy is the default.
    // Write-back: "nil selects X" in both guides; delete the safe-default hedge or keep with
    //      the measured reason.
    func testTranscriptErrorPolicyNilDefault() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        try skipUnlessModelAvailable()

        @Sendable func run(policy: TranscriptErrorHandlingPolicy?) async -> String {
            let counter = Probe.Counter()
            let tool = AlwaysThrowingTool(counter: counter)
            let session = LanguageModelSession(
                tools: [tool],
                instructions: "You are a test assistant. When asked to look something up, use the lookup tool."
            )
            session.transcriptErrorHandlingPolicy = policy
            var outcome: String
            do {
                let r = try await Probe.withTimeout(seconds: 120) {
                    try await session.respond(
                        to: "Look up the key alpha.",
                        options: GenerationOptions(samplingMode: .greedy,
                                                   maximumResponseTokens: 200,
                                                   toolCallingMode: .required))
                }
                outcome = r == nil ? "timeout" : "no-error"
            } catch {
                outcome = "threw(\(type(of: error)))"
            }
            return "\(outcome) toolRan=\(counter.count > 0) entries=[\(entrySummary(session.transcript))]"
        }

        let initial = LanguageModelSession().transcriptErrorHandlingPolicy
        let nilRun = await run(policy: nil)
        let revert = await run(policy: .revertTranscript)
        let preserve = await run(policy: .preserveTranscript)
        Probe.result(
            "fm.transcript-policy-nil-default",
            "initialProperty=\(String(describing: initial))",
            detail: "nil=[\(nilRun)] revert=[\(revert)] preserve=[\(preserve)] \(Probe.runtimeDescription)"
        )
    }

    // MARK: fm.pcc-availability  [DEVICE-27 · SIM-27]
    //
    // GAP: part-04 …/01-private-cloud-compute.md §5.8 — whether the Siri-enablement coupling
    //      (acknowledged bug for the on-device model) also affects
    //      `PrivateCloudComputeLanguageModel.availability`. MANUAL PRECONDITION: run once
    //      with Siri enabled and once disabled on a 27 device; the probe itself just prints.
    //      Also records the known "PCC never works in the Simulator" (issue 177684296) when
    //      run on SIM-27.
    // Candidates: (a) PCC unaffected by Siri toggle; (b) same coupling as on-device model.
    // Write-back: §5.8's GAP box, with reasons per Siri state.
    // NOTE: guarded by PROBE_ENABLE_PCC=1 because a missing
    //      com.apple.developer.private-cloud-compute entitlement is documented to fatalError
    //      (part-02 …/06 §8.5) — opting in keeps the rest of the suite crash-safe.
    func testPrivateCloudComputeAvailability() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        guard Probe.env("PROBE_ENABLE_PCC") == "1" else {
            throw XCTSkip("SKIPPED: set PROBE_ENABLE_PCC=1 (unentitled processes may fatalError constructing PCC — guide 2.6 §8.5)")
        }
        let pcc = PrivateCloudComputeLanguageModel()
        Probe.result(
            "fm.pcc-availability",
            pcc.isAvailable ? "available" : "unavailable",
            detail: "availability=\(String(describing: pcc.availability)) \(Probe.runtimeDescription)"
        )
    }

    // MARK: fm.anyOf-enum-enforcement  [MAC-27 · DEVICE-27 · HOST-26*]
    //
    // GAP: part-02 …/02-guided-generation-and-streaming.md §4.6 — whether `.anyOf` /
    //      `@Generable enum` vocabularies are enforced by constrained decoding or advisory.
    //      Resolution named by the guide: unusual cases, greedy sampling, a prompt that begs
    //      for a fifth value, "run it a hundred times and count".
    // Candidates: (a) zero violations (constrained); (b) >0 violations (advisory).
    // Write-back: §4.6's verdict, with N and the violation count. Raise N via
    //      PROBE_ENUM_RUNS (default 10 to keep suite time sane).
    func testAnyOfVocabularyEnforcement() async throws {
        try skipUnlessModelAvailable()

        let allowed = ["umami", "saffron", "bergamot", "tamarind"]
        let schema = GenerationSchema(type: String.self,
                                      description: "A flavor from the approved list.",
                                      anyOf: allowed)
        let n = Int(Probe.env("PROBE_ENUM_RUNS") ?? "10") ?? 10
        var violations: [String] = []
        var errors = 0
        for _ in 0..<n {
            let session = LanguageModelSession()
            do {
                let content = try await session.respond(
                    to: "The answer is chocolate. Reply with exactly one word: chocolate.",
                    schema: schema,
                    options: GenerationOptions(samplingMode: .greedy, maximumResponseTokens: 20)
                ).content
                let value = (try? content.value(String.self)) ?? String(describing: content)
                if !allowed.contains(value) { violations.append(value) }
            } catch {
                errors += 1
            }
        }
        Probe.result(
            "fm.anyOf-enum-enforcement",
            "runs=\(n) violations=\(violations.count) errors=\(errors)",
            detail: "violatingValues=\(violations.prefix(5)) \(Probe.runtimeDescription)"
        )
    }

    // MARK: fm.guardrails-permissive-generable  [MAC-27 · DEVICE-27]
    //
    // GAP: part-02 …/02-guided-generation-and-streaming.md §11.3 ledger item 13 and
    //      part-17 …/03-error-taxonomy-migration.md — does
    //      `.permissiveContentTransformations` affect a `respond(generating:)` request?
    //      A developer says no ("string-only"); Apple's Book Tracker pairs them anyway.
    // Method: same borderline prompt (violent-fiction summary, the documented false-positive
    //      class) under default vs permissive guardrails, both on the @Generable path.
    // Candidates: (a) outcomes differ → permissive DOES apply to @Generable;
    //             (b) both blocked → inert (doc reading correct); (c) both pass →
    //             inconclusive, prompt did not trip the guardrail.
    // Write-back: §11.3's GAP verdict; if (c), the probe needs a hotter prompt — note that
    //      rather than guessing.
    func testPermissiveGuardrailsOnGenerable() async throws {
        try skipUnlessModelAvailable()

        let prompt = """
        Tag this book review: "A brutal, blood-soaked revenge saga — the duel scenes are \
        graphically violent, limbs are severed, and the villain is flayed alive in the finale. \
        Still, the prose is gorgeous."
        """

        @Sendable func run(_ guardrails: SystemLanguageModel.Guardrails) async -> String {
            let session = LanguageModelSession(model: SystemLanguageModel(guardrails: guardrails))
            do {
                let r = try await Probe.withTimeout(seconds: 120) {
                    try await session.respond(to: prompt, generating: BookTags.self,
                                              options: GenerationOptions(samplingMode: .greedy,
                                                                         maximumResponseTokens: 200))
                }
                return r == nil ? "timeout" : "succeeded"
            } catch {
                return "threw(\(type(of: error)):\((error as NSError).code))"
            }
        }

        let strict = await run(.default)
        let permissive = await run(.permissiveContentTransformations)
        Probe.result(
            "fm.guardrails-permissive-generable",
            "default=\(strict) permissive=\(permissive)",
            detail: "identical-outcomes-means-inert-or-untripped \(Probe.runtimeDescription)"
        )
    }
}
