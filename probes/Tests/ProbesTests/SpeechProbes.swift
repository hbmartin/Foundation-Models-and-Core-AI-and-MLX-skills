// SpeechProbes — executable evidence for the open Speech-framework behavioral
// gaps in the guide series.
//
// Destinations (see probes/README.md):
//   HOST-26   runs on the authoring host today (macOS 26.5, `swift test`)
//   SIM-27    runs on the iOS 27.0 Simulator today (xcodebuild test)
//   MAC-27    needs a Mac running macOS 27 (upgrade day)
//   DEVICE-27 needs a physical device on iOS/macOS 27
//
// Probes never fake a pass/fail: measuring probes print PROBE-RESULT and pass.

#if canImport(Speech)
import Foundation
import Speech
import ProbeSupport
import XCTest

final class SpeechProbes: XCTestCase {

    // MARK: speech.assetInventory-status-order  [HOST-26 · SIM-27 · MAC-27 · DEVICE-27]
    //
    // GAP: guides/part-16-adjacent-capabilities/references/01-speech-analyzer-end-to-end.md
    //      §5.2 GAP box + gap table G2, and notes/NEXT-BETA-CHECKLIST.md §7.
    //      `AssetInventory.Status` is `Comparable`, and the case DECLARATION ORDER differs
    //      between the captured interfaces — 26.5: unsupported, supported, downloading,
    //      installed; 27.0: unsupported, downloading, supported, installed
    //      (Speech-26.5-macos.swiftinterface:23-28 / Speech-27.0-macos.swiftinterface:44-50).
    //      An interface cannot distinguish a synthesized `<` (declaration-order semantics,
    //      meaning the ORDERING CHANGED between OS generations) from a hand-written one
    //      (identical semantics on both). Only a runtime sort decides.
    // Candidates: (a) 26-order unsupported < supported < downloading < installed;
    //             (b) 27-order unsupported < downloading < supported < installed;
    //             (c) some hand-written ordering identical on both generations.
    // Write-back: the sorted array per OS generation into 16.1 §5.2 + G2; tick the
    //      NEXT-BETA-CHECKLIST §7 runtime-probe box. If HOST-26 and SIM-27 disagree, the
    //      ordering is synthesized and code comparing Status across OS versions is wrong.
    func testAssetInventoryStatusOrdering() {
        let sorted = [AssetInventory.Status.installed, .downloading, .supported, .unsupported].sorted()
        let all: [AssetInventory.Status] = [.unsupported, .supported, .downloading, .installed]
        // Redundant pairwise matrix so a single harvested line carries the full relation.
        let pairs = all.flatMap { a in
            all.compactMap { b -> String? in
                a == b ? nil : "\(a)<\(b)=\(a < b)"
            }
        }.joined(separator: " ")
        Probe.result(
            "speech.assetInventory-status-order",
            "sorted=[\(sorted.map { "\($0)" }.joined(separator: ","))]",
            detail: "\(pairs) \(Probe.runtimeDescription)"
        )
    }
}
#endif
