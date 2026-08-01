// SpotlightProbes — executable evidence for the SpotlightSearchTool gaps in
// guide part-02 ref 04, using the `_CoreSpotlight_FoundationModels` cross-import
// overlay (activated by importing CoreSpotlight AND FoundationModels together).
//
// Destinations (see probes/README.md):
//   SIM-27    runs on the iOS 27.0 Simulator today (xcodebuild test) — the test
//             runner is a real app with a container, so Core Spotlight donation
//             is at least attemptable there; this is what converts the old
//             "needs a signed app container" SKIPPED row into a measurement.
//   MAC-27 · DEVICE-27  upgrade-day / device harvests.
//   HOST-26   both probes XCTSkip (the overlay surface is 27-only).
//
// Probes never fake a pass/fail: every step records its outcome or error
// fingerprint; no step asserts.

#if canImport(CoreSpotlight) && canImport(FoundationModels)
import Foundation
import CoreSpotlight
import FoundationModels
import ProbeSupport
import XCTest

final class SpotlightProbes: XCTestCase {

    // MARK: fm.spotlight-tool-surface  [SIM-27 · MAC-27 · DEVICE-27]
    //
    // GAP: part-02 …/04-spotlight-rag-and-system-tools.md §7 — the tool's declared name is
    //      hand-asserted ("spotlight_search", from Apple sample code), and its `parameters`
    //      GenerationSchema (the exact argument keys the model is guided toward) is
    //      published NOWHERE — not in docs, not in the overlay interface (Arguments is just
    //      a GeneratedContent typealias, _CoreSpotlight_FoundationModels-27.0:385-388).
    // Candidates: any — this is a pure recording.
    // Write-back: 2.4 §7 (schema dump verbatim) + 2.3 §2 (confirm or correct the
    //      hand-declared tool name).
    func testSpotlightToolSurface() throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        let tool = SpotlightSearchTool()
        Probe.result(
            "fm.spotlight-tool-surface",
            "name=\(tool.name) includesSchema=\(tool.includesSchemaInInstructions)",
            detail: "parameters=\(String(describing: tool.parameters).prefix(8000)) \(Probe.runtimeDescription)"
        )
    }

    // MARK: fm.spotlight-direct-call  [SIM-27 · MAC-27 · DEVICE-27]
    //
    // GAP: part-02 …/04-spotlight-rag-and-system-tools.md §7/§7.1 and the probes/README
    //      SKIPPED row, which claimed the delegate/tool path "needs a signed app container
    //      with a populated Core Spotlight index". The xcodebuild test runner IS an app with
    //      a container, and `Arguments == GeneratedContent` means `call(arguments:)` is
    //      invocable DIRECTLY — no model, no tool-calling assets (which the sim lacks).
    // Method (every step records, none asserts):
    //      1. record CSSearchableIndex.isIndexingAvailable()
    //      2. donate 3 CSSearchableItems carrying a UUID nonce; record outcome
    //      3. start reading tool.searchResults in a task
    //      4. call tool.call(arguments:) with {"query": "<nonce>"}; record output or error
    //      5. record the first SearchReply (or timeout)
    //      6. delete the donated domain
    // Candidates: (a) donation + direct call work in the runner container → the SKIPPED row
    //             becomes a measurement; (b) donation fails → its error fingerprint replaces
    //             the hand-waved skip reason; (c) call() throws a schema mismatch → the
    //             ParsingError text documents the real Arguments shape.
    // Write-back: 2.4 §7/§7.1 + the probes/README SKIPPED-table row (either direction is
    //      progress).
    func testSpotlightDirectCall() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        var rows: [String] = []
        rows.append("indexingAvailable=\(CSSearchableIndex.isIndexingAvailable())")

        let nonce = String(UUID().uuidString.prefix(8))
        let domain = "probe.spotlight"
        let items: [CSSearchableItem] = (0..<3).map { i in
            let attributes = CSSearchableItemAttributeSet(contentType: .text)
            attributes.title = "Probe note \(nonce) number \(i)"
            attributes.contentDescription = "A searchable probe item containing the nonce \(nonce)."
            return CSSearchableItem(uniqueIdentifier: "probe-\(nonce)-\(i)",
                                    domainIdentifier: domain,
                                    attributeSet: attributes)
        }
        do {
            try await CSSearchableIndex.default().indexSearchableItems(items)
            rows.append("donate=ok")
        } catch {
            let ns = error as NSError
            rows.append("donate=threw(\(ns.domain):\(ns.code):\(String(describing: error).prefix(120)))")
        }
        // Give the index a beat to commit before querying.
        try? await Task.sleep(for: .seconds(2))

        let tool = SpotlightSearchTool()
        // Reader started before the calls so an immediately-emitted reply is not missed.
        let repliesTask = Task { () -> String in
            var collected: [String] = []
            for await reply in tool.searchResults {
                collected.append(String(String(describing: reply).prefix(400)))
                if collected.count >= 2 { break }
            }
            return collected.joined(separator: " ⫽ ")
        }
        // Call 1 — deliberately naive shape. Measured 2026-07-31 (sim): the tool does NOT
        // throw on malformed arguments; it RETURNS a structured JSON error inside the
        // Prompt output (code 100, "Malformed tool arguments — retry with the schema
        // below") that self-describes FullArguments. Keep recording that behavior.
        do {
            let args = try GeneratedContent(json: #"{"query":"\#(nonce)"}"#)
            let output = try await Probe.withTimeout(seconds: 60) { () -> String in
                let result = try await tool.call(arguments: args)
                return String(String(describing: result).prefix(600))
            }
            rows.append("naiveCall=\(output.map { "ok output=\($0)" } ?? "timeout")")
        } catch {
            rows.append("naiveCall=threw(\(errorFingerprint(error)))")
        }
        // Call 2 — the FullArguments shape the tool's own error prescribes:
        //   {"query":{"type":"search","value":{"root":{"type":"allText","terms":[…]},"pageSize":15}}}
        do {
            let args = try GeneratedContent(
                json: #"{"query":{"type":"search","value":{"root":{"type":"allText","terms":["\#(nonce)"]},"pageSize":15}}}"#)
            let output = try await Probe.withTimeout(seconds: 60) { () -> String in
                let result = try await tool.call(arguments: args)
                return String(String(describing: result).prefix(1200))
            }
            rows.append("schemaCall=\(output.map { "ok output=\($0)" } ?? "timeout")")
        } catch {
            rows.append("schemaCall=threw(\(errorFingerprint(error)))")
        }
        // Call 3 — same FullArguments shape but built with init(properties:), whose
        // KeyValuePairs PRESERVES key order (Kind.structure carries orderedKeys) —
        // measured: GeneratedContent(json:) alphabetizes keys on re-serialization, and
        // the tool's decoder rejected the prescribed shape with type-after-terms, so
        // order preservation is the live hypothesis for making a direct call decode.
        do {
            let orderedArgs = GeneratedContent(properties: [
                "query": GeneratedContent(properties: [
                    "type": "search",
                    "value": GeneratedContent(properties: [
                        "root": GeneratedContent(properties: [
                            "type": "allText",
                            "terms": [nonce],
                        ]),
                        "pageSize": 15,
                    ]),
                ]),
            ])
            let output = try await Probe.withTimeout(seconds: 60) { () -> String in
                let result = try await tool.call(arguments: orderedArgs)
                return String(String(describing: result).prefix(1200))
            }
            rows.append("orderedCall=\(output.map { "ok output=\($0)" } ?? "timeout")")
        } catch {
            rows.append("orderedCall=threw(\(errorFingerprint(error)))")
        }
        let reply = (try? await Probe.withTimeout(seconds: 15) { await repliesTask.value }) ?? nil
        if let reply {
            rows.append("searchReplies=[\(reply)]")
        } else {
            repliesTask.cancel()
            rows.append("searchReplies=timeout")
        }
        try? await CSSearchableIndex.default().deleteSearchableItems(withDomainIdentifiers: [domain])
        Probe.result("fm.spotlight-direct-call",
                     rows.first(where: { $0.hasPrefix("call=") })?.prefix(40).description ?? "recorded",
                     detail: "\(rows.joined(separator: " ")) \(Probe.runtimeDescription)")
    }
}
#endif
