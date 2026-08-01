// EvaluationsProbes — executable evidence for the open Evaluations-framework gaps.
//
// Evaluations ships inside Xcode (next to XCTest/Testing in the platform's
// Developer/Library/Frameworks), is gated `@available(anyAppleOS 27.0, *)`, and —
// crucially — `Evaluation.run(info:)` is a public API, so an evaluation can run
// programmatically inside XCTest with a canned, model-free subject. That makes
// most of these probes pure logic probes: runnable on the iOS 27.0 Simulator
// TODAY, no Apple Intelligence assets needed.
//
// The whole file is compile-guarded so the package builds where the framework is
// absent (e.g. a bare toolchain without Xcode).

#if canImport(Evaluations)
import Evaluations
import Foundation
import FoundationModels
import ProbeSupport
import XCTest

// MARK: - Offline evaluation harness (no model involved)

@available(macOS 27.0, iOS 27.0, *)
private struct FixedSample: SampleProtocol {
    var input: String
    var expected: Double?
}

/// An Evaluation whose subject comes from a canned closure — never from a model.
@available(macOS 27.0, iOS 27.0, *)
private struct OfflineEvaluation<S: SampleProtocol>: Evaluation
where S.ExpectedValue: Codable & Sendable {
    typealias Subject = ModelSubject<S.ExpectedValue>

    var samples: [S]
    var makeSubject: @Sendable (S) async throws -> ModelSubject<S.ExpectedValue>
    var evaluatorList: [any EvaluatorProtocol<S, ModelSubject<S.ExpectedValue>>]
    /// Metrics registered with computeMean — REQUIRED for aggregateValue to work:
    /// measured 2026-07-31 on the 27.0 sim, an evaluation whose aggregateMetrics
    /// registers nothing yields an empty summary DataFrame and aggregateValue
    /// returns the sentinel -1.0 for every metric.
    var aggregateMeans: [Metric] = []

    var dataset: ArrayLoader<S> { ArrayLoader(samples: samples) }
    func subject(from sample: S) async throws -> Subject { try await makeSubject(sample) }
    var evaluators: [any EvaluatorProtocol<S, Subject>] {
        // Explicit `return` suppresses the EvaluatorsBuilder transform.
        return evaluatorList
    }
    func aggregateMetrics(using aggregator: inout MetricsAggregator) {
        for metric in aggregateMeans { aggregator.computeMean(of: metric) }
    }
}

final class EvaluationsProbes: XCTestCase {

    private func requireOS27() throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
    }

    // MARK: eval.metric-identity  [SIM-27 · MAC-27]
    //
    // GAP: part-06 …/01-foundations-and-hill-climbing.md §8.2 (restated §17) — is `Metric`
    //      identity by NAME or by INSTANCE? Apple's minimal example constructs
    //      Metric("Match") inside the evaluator closure (name-keyed reading); Book
    //      Tracker's static-let structure implies instance-keyed. The interface's
    //      hand-written == is consistent with either. Guide-named experiment: two
    //      Metric("X") values in one evaluation; one column or two?
    // Candidates: (a) one column + aggregateValue reachable via a FRESH Metric("X")
    //             → identity by name; (b) two columns / fresh-instance lookup fails
    //             → identity by instance.
    // Write-back: §8.2's GAP box + the §17 safe-default (which is correct either way,
    //      but the reason changes).
    func testMetricIdentityByNameOrInstance() async throws {
        try requireOS27()
        guard #available(macOS 27.0, iOS 27.0, *) else { return }

        let evaluation = OfflineEvaluation<FixedSample>(
            samples: [FixedSample(input: "a", expected: 1),
                      FixedSample(input: "b", expected: 0)],
            makeSubject: { ModelSubject(value: $0.expected ?? 0) },
            evaluatorList: [
                // Two separate evaluators, each constructing a FRESH Metric("Match").
                Evaluator<FixedSample> { _, subject in
                    Metric("Match").scoring(subject.value)
                },
                Evaluator<FixedSample> { _, subject in
                    Metric("Match").scoring(1.0 - subject.value)
                },
            ],
            aggregateMeans: [Metric("Match")]
        )
        let result = try await evaluation.run()
        let summaryColumns = result.summary.columns.map(\.name)
        let detailedColumns = result.detailed.columns.map(\.name)
        let freshLookup = result.aggregateValue(.mean(of: Metric("Match")))
        Probe.result(
            "eval.metric-identity",
            "summaryColumns=\(summaryColumns)",
            detail: "detailedColumns=\(detailedColumns) meanViaFreshInstance=\(freshLookup) \(Probe.runtimeDescription)"
        )
    }

    // MARK: eval.mean-over-all-ignored  [SIM-27 · MAC-27]
    //
    // GAP: part-06 …/01-foundations-and-hill-climbing.md §17.5 — what
    //      aggregateValue(.mean(of:)) returns when EVERY sample was `.ignore()`d.
    //      Zero passes nothing; NaN fails everything; 1.0 would silently pass a suite
    //      measuring nothing.
    // Candidates: (a) 0.0; (b) NaN; (c) 1.0; (d) trap.
    // Write-back: §17.5's GAP box; if (c), promote the row-count assertion from
    //      "safe default" to "required".
    func testMeanAggregateOverAllIgnored() async throws {
        try requireOS27()
        guard #available(macOS 27.0, iOS 27.0, *) else { return }

        let ignored = Metric("AlwaysIgnored")
        let evaluation = OfflineEvaluation<FixedSample>(
            samples: (0..<4).map { FixedSample(input: "s\($0)", expected: nil) },
            makeSubject: { _ in ModelSubject(value: 0) },
            evaluatorList: [
                Evaluator<FixedSample> { _, _ in ignored.ignore(rationale: "prompt-only sample") },
            ],
            aggregateMeans: [ignored]
        )
        let result = try await evaluation.run()
        let mean = result.aggregateValue(.mean(of: ignored))
        Probe.result(
            "eval.mean-over-all-ignored",
            mean.isNaN ? "NaN" : "\(mean)",
            detail: "detailedRows=\(result.detailed.rows.count) \(Probe.runtimeDescription)"
        )
    }

    // MARK: eval.subject-throws  [SIM-27 · MAC-27]
    //
    // GAP: part-06 …/01-foundations-and-hill-climbing.md §17.7 — when subject(from:)
    //      throws for SOME samples, does the run abort, fail, or silently drop those
    //      samples from the aggregate? (Interface hint: missing metrics become "ignored
    //      columns and logged", which leans drop-silently — unproven for subject errors.)
    // Candidates: (a) run() throws (abort); (b) samples dropped, aggregate over the rest;
    //             (c) samples scored as failing.
    // Write-back: §17.7's GAP box; if (b), the guide's "a run that silently drops its
    //      five hardest samples reports an improved score" warning graduates to VERIFIED.
    func testSubjectInferenceFailureHandling() async throws {
        try requireOS27()
        guard #available(macOS 27.0, iOS 27.0, *) else { return }

        let match = Metric("Match")
        let evaluation = OfflineEvaluation<FixedSample>(
            samples: [FixedSample(input: "good-1", expected: 1),
                      FixedSample(input: "bad", expected: nil),
                      FixedSample(input: "good-2", expected: 1),
                      FixedSample(input: "also-bad", expected: nil),
                      FixedSample(input: "good-3", expected: 1)],
            makeSubject: { sample in
                guard sample.expected != nil else {
                    throw SubjectInferenceError.failed(reason: "probe: deliberate per-sample failure")
                }
                return ModelSubject(value: 1)
            },
            evaluatorList: [
                Evaluator<FixedSample> { _, subject in
                    subject.value == 1 ? match.passing() : match.failing()
                },
            ],
            aggregateMeans: [match]
        )
        do {
            let result = try await evaluation.run()
            Probe.result(
                "eval.subject-throws",
                "run-completed",
                detail: "samples=5 subjectFailures=2 detailedRows=\(result.detailed.rows.count) meanMatch=\(result.aggregateValue(.mean(of: match))) \(Probe.runtimeDescription)"
            )
        } catch {
            Probe.result(
                "eval.subject-throws",
                "run-threw",
                detail: "type=\(type(of: error)) desc=\(String(describing: error).prefix(200)) \(Probe.runtimeDescription)"
            )
        }
    }

    // MARK: eval.disallowed-arguments-narrowing  [SIM-27 · MAC-27]
    //
    // GAP: part-06 …/03-synthetic-data-and-tool-trajectories.md §"What to put in
    //      disallowed" — `disallowed:` takes [ToolExpectation], so an entry CAN carry
    //      argument matchers; whether those matchers NARROW the prohibition ("never with
    //      these arguments") or the name alone bans the tool is unverified.
    // Method: trajectory calls searchBooks(mood: "uplifting").
    //      Case A disallows searchBooks WITH .exact(mood: "dark")   → passes iff narrowed.
    //      Case B disallows searchBooks WITH .exact(mood: "uplifting") → must fail either way
    //      (sanity check that the matcher is even consulted).
    // Candidates: (a) A passes, B fails → arguments narrow; (b) A and B both fail →
    //             name-wide ban, matchers ignored on disallowed; (c) A and B both pass →
    //             matchers consulted but disallowed-with-args broken.
    // Write-back: the §GAP box + the ledger row "semantics of disallowed arguments".
    func testDisallowedArgumentsNarrowing() async throws {
        try requireOS27()
        guard #available(macOS 27.0, iOS 27.0, *) else { return }

        @Sendable func run(disallowedMood: String) async throws -> (Double, Double, Substring) {
            let allPass = Metric("Trajectory")
            let pctPass = Metric("TrajectoryPct")
            let expectations = TrajectoryExpectation(
                ordered: [],
                unordered: [],
                disallowed: [ToolExpectation("searchBooks",
                                             arguments: [.exact(argumentName: "mood",
                                                                value: .string(disallowedMood))])]
            )
            let sample = ModelSample<Double>(prompt: "find me a book", expected: 1.0,
                                             expectations: expectations)
            let transcript = StructuredTranscript(
                toolCalls: [Transcript.ToolCall(
                    id: "c1",
                    toolName: "searchBooks",
                    arguments: GeneratedContent(properties: ["mood": "uplifting"]))]
            )
            let evaluation = OfflineEvaluation<ModelSample<Double>>(
                samples: [sample],
                makeSubject: { _ in ModelSubject(value: 1.0, transcript: transcript) },
                evaluatorList: [ToolCallEvaluator<ModelSample<Double>>(allPass: allPass,
                                                                       percentagePass: pctPass)],
                aggregateMeans: [allPass, pctPass]
            )
            let result = try await evaluation.run()
            return (result.aggregateValue(.mean(of: allPass)),
                    result.aggregateValue(.mean(of: pctPass)),
                    String(describing: result.detailed).prefix(500))
        }

        do {
            let narrowed = try await run(disallowedMood: "dark")       // args differ from call
            let matching = try await run(disallowedMood: "uplifting")  // args match call
            Probe.result(
                "eval.disallowed-arguments-narrowing",
                "differentArgs(allPass=\(narrowed.0)) matchingArgs(allPass=\(matching.0))",
                detail: "differentArgsPct=\(narrowed.1) matchingArgsPct=\(matching.1) — differentArgs=1.0 with matchingArgs=0.0 means arguments DO narrow — differentArgsFrame: \(narrowed.2) — matchingArgsFrame: \(matching.2) \(Probe.runtimeDescription)"
            )
        } catch {
            Probe.result("eval.disallowed-arguments-narrowing", "threw",
                         detail: "type=\(type(of: error)) desc=\(String(describing: error).prefix(200)) \(Probe.runtimeDescription)")
        }
    }

    // MARK: eval.allowsAdditionalCalls-false  [SIM-27 · MAC-27]
    //
    // GAP: part-06 …/03-synthetic-data-and-tool-trajectories.md §quick-reference ledger —
    //      `allowsAdditionalCalls` default is SDK-verified `= true`; the SEMANTICS of
    //      `false` are the GAP: does an unexpected extra call fail the trajectory, and
    //      does it hit allPass, percentagePass, or both?
    // Method: expectation = exactly one searchBooks call, allowsAdditionalToolCalls:
    //      false; trajectory makes searchBooks + an extra logEvent call. Control run
    //      without the extra call.
    // Candidates: (a) extra call fails allPass (strict); (b) ignored (flag inert);
    //             (c) affects percentagePass only.
    // Write-back: the ledger row + §"What to put in disallowed" contrast with disallowed.
    func testAllowsAdditionalCallsFalseSemantics() async throws {
        try requireOS27()
        guard #available(macOS 27.0, iOS 27.0, *) else { return }

        @Sendable func run(extraCall: Bool) async throws -> (Double, Double, Substring) {
            let allPass = Metric("Trajectory")
            let pctPass = Metric("TrajectoryPct")
            let expectations = TrajectoryExpectation(
                ordered: [ToolExpectation("searchBooks")],
                unordered: [],
                allowsAdditionalToolCalls: false
            )
            let sample = ModelSample<Double>(prompt: "find me a book", expected: 1.0,
                                             expectations: expectations)
            var calls = [Transcript.ToolCall(
                id: "c1", toolName: "searchBooks",
                arguments: GeneratedContent(properties: ["mood": "uplifting"]))]
            if extraCall {
                calls.append(Transcript.ToolCall(
                    id: "c2", toolName: "logEvent",
                    arguments: GeneratedContent(properties: ["event": "search"])))
            }
            let transcript = StructuredTranscript(toolCalls: calls)
            let evaluation = OfflineEvaluation<ModelSample<Double>>(
                samples: [sample],
                makeSubject: { _ in ModelSubject(value: 1.0, transcript: transcript) },
                evaluatorList: [ToolCallEvaluator<ModelSample<Double>>(allPass: allPass,
                                                                       percentagePass: pctPass)],
                aggregateMeans: [allPass, pctPass]
            )
            let result = try await evaluation.run()
            return (result.aggregateValue(.mean(of: allPass)),
                    result.aggregateValue(.mean(of: pctPass)),
                    String(describing: result.detailed).prefix(500))
        }

        do {
            let control = try await run(extraCall: false)
            let extra = try await run(extraCall: true)
            Probe.result(
                "eval.allowsAdditionalCalls-false",
                "control(allPass=\(control.0)) withExtraCall(allPass=\(extra.0))",
                detail: "controlPct=\(control.1) withExtraCallPct=\(extra.1) — control=1.0 with extra=0.0 means false is enforced — controlFrame: \(control.2) — extraFrame: \(extra.2) \(Probe.runtimeDescription)"
            )
        } catch {
            Probe.result("eval.allowsAdditionalCalls-false", "threw",
                         detail: "type=\(type(of: error)) desc=\(String(describing: error).prefix(200)) \(Probe.runtimeDescription)")
        }
    }

    // MARK: eval.generator-unreachable-target  [MAC-27 · DEVICE-27]
    //
    // GAP: part-06 …/03-synthetic-data-and-tool-trajectories.md §3 — when the validator is
    //      strict enough that targetCount is unreachable, does SampleGenerator.run() retry
    //      forever, give up after an internal budget, or throw? Also instruments the §5
    //      observability question by counting sessionProvider invocations.
    // Candidates: (a) throws; (b) finishes short; (c) still running at the 120 s bound
    //             (consistent with retry-forever; the guide's "bound by wall-clock" advice
    //             stands verified).
    // Write-back: §3's GAP box with the outcome and invocation count.
    // NOTE: needs a live model (generation), so MAC-27/DEVICE-27, not SIM today.
    func testSampleGeneratorUnreachableTarget() async throws {
        try requireOS27()
        guard #available(macOS 27.0, iOS 27.0, *) else { return }
        guard SystemLanguageModel.default.isAvailable else {
            throw XCTSkip("SystemLanguageModel unavailable: \(SystemLanguageModel.default.availability)")
        }

        let invocations = Probe.Counter()
        let generator = SampleGenerator<ModelSample<String>>(
            Prompt("Generate one-sentence book blurbs."),
            samples: [ModelSample<String>(prompt: "seed blurb", expected: "A cozy mystery.")],
            targetCount: 5,
            sessionProvider: {
                invocations.increment()
                return LanguageModelSession()
            },
            validator: { _ in false } // every generated sample is invalid → target unreachable
        )
        let outcome: String
        // Counted outside the timeout closure so the partial tally survives
        // a deadline or a throw instead of dying with the abandoned closure.
        let producedSoFar = Probe.Counter()
        do {
            let bounded = try await Probe.withTimeout(seconds: 120) { () -> Int in
                for try await _ in generator.run() { producedSoFar.increment() }
                return producedSoFar.count
            }
            switch bounded {
            case .value(let produced): outcome = "finished(produced=\(produced))"
            case .timedOut: outcome = "still-running-at-120s(produced=\(producedSoFar.count))"
            }
        } catch {
            outcome = "threw(\(type(of: error)): \(String(describing: error).prefix(160)))"
                + " produced=\(producedSoFar.count)"
        }
        let counts = await (generator.samples.count, generator.invalidSamples.count)
        Probe.result(
            "eval.generator-unreachable-target",
            outcome,
            detail: "sessionProviderInvocations=\(invocations.count) samples=\(counts.0) invalidSamples=\(counts.1) \(Probe.runtimeDescription)"
        )
    }
}
#endif
