// CoreAIProbes — executable evidence for the open Core AI behavioral gaps.
//
// CoreAI is a 27.0-only framework with no 26-era API, so the whole file is
// compile-guarded with `#if canImport(CoreAI)`: the package still builds against
// an SDK that lacks the module, and on OS < 27 every probe records
// "SKIPPED: needs OS 27".
//
// MEASURED 2026-07-31: CoreAI is ABSENT from the iPhoneSimulator27.0 SDK
// (present in iPhoneOS27.0.sdk: CoreAI.framework + the six SubFrameworks; the
// simulator SDK ships none of them), so `canImport` excludes this whole file
// from simulator builds — there is no SIM-27 destination for Core AI at all in
// this beta. That is itself a finding for guide 7.1 ("can you develop Core AI
// against the Simulator": no). Destinations below are MAC-27 / DEVICE-27 only.
//
// Two probe classes here:
//  * asset-free probes (deviceArchitectureName, SpecializationOptions defaults,
//    NDArray zero-init) — run the moment any OS 27 machine exists;
//  * asset-dependent probes (the AIModelCache family) — need a compiled
//    `.aimodel`/`.aimodelc` on disk. Pass its path via PROBE_AIMODEL_URL; they
//    XCTSkip otherwise. Produce an asset with `xcrun aimodelc package|compile
//    --output …` or `xcrun coreai-build compile|package …` — coreai-build ships
//    in the optional Metal Toolchain component (`xcodebuild -downloadComponent
//    MetalToolchain`; resolve it via `xcrun --no-cache --find coreai-build`) —
//    see notes/NEEDED-FROM-A-MACOS-27-MACHINE.md item 2 (resolved 2026-07-31).

#if canImport(CoreAI)
import CoreAI
import Foundation
import ProbeSupport
import XCTest

private func modelURLFromEnvironment() throws -> URL {
    guard let path = Probe.env("PROBE_AIMODEL_URL") else {
        throw XCTSkip("SKIPPED: set PROBE_AIMODEL_URL to a compiled .aimodel/.aimodelc to run cache probes")
    }
    return URL(fileURLWithPath: path)
}

final class CoreAIProbes: XCTestCase {

    // MARK: coreai.deviceArchitectureName  [MAC-27 · DEVICE-27 — no sim: CoreAI absent from the simulator SDK]
    //
    // GAP: part-15 …/01-model-distribution-and-updates.md §4.4 — the architecture-code
    //      enumeration is community-sourced and contested (h16c vs h16s on M4 Max; only
    //      h18p attested for iPhone 17 Pro). The guide: "printing
    //      AIModel.deviceArchitectureName on one device of each family … is the only
    //      authoritative source."
    // Candidates: any string; suffix letters p/g/s/c are the interesting part.
    // Write-back: a row per machine in §4.4's table (code → hw.model). Run on every
    //      device family you can reach.
    func testDeviceArchitectureName() throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        var size = 0
        sysctlbyname("hw.model", nil, &size, nil, 0)
        var buf = [UInt8](repeating: 0, count: max(size, 1))
        sysctlbyname("hw.model", &buf, &size, nil, 0)
        let hwModel = String(decoding: buf.prefix(while: { $0 != 0 }), as: UTF8.self)
        Probe.result(
            "coreai.deviceArchitectureName",
            AIModel.deviceArchitectureName,
            detail: "hw.model=\(hwModel) \(Probe.runtimeDescription)"
        )
    }

    // MARK: coreai.specializationOptions-defaults  [MAC-27 · DEVICE-27 — no sim]
    //
    // GAP: part-07 …/01-runtime-and-ndarray.md §4.3 / §16.3 item 7 —
    //      `SpecializationOptions.expectFrequentReshapes`' default value is unknown
    //      (a swiftinterface does not print stored-property defaults). Also harvests
    //      `.default` vs `.cpuOnly` compute-unit sets and `ComputeUnitKind.availableKinds`
    //      per destination (feeds part-10's compute-unit routing discussion).
    // Candidates: expectFrequentReshapes = true | false.
    // Write-back: the default value in §4.3; the availableKinds sets per destination in
    //      part-10 …/01-ane-vs-gpu-authoring-rules.md §8.
    func testSpecializationOptionsDefaults() throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        let def = SpecializationOptions.default
        let cpu = SpecializationOptions.cpuOnly
        Probe.result(
            "coreai.specializationOptions-defaults",
            "default.expectFrequentReshapes=\(def.expectFrequentReshapes)",
            detail: "default.allowed=\(def.allowedComputeUnitKinds) default.preferred=\(String(describing: def.preferredComputeUnitKind)) cpuOnly.allowed=\(cpu.allowedComputeUnitKinds) cpuOnly.expectFrequentReshapes=\(cpu.expectFrequentReshapes) availableKinds=\(ComputeUnitKind.availableKinds) \(Probe.runtimeDescription)"
        )
    }

    // MARK: coreai.ndarray-zero-init  [MAC-27 · DEVICE-27 — no sim]
    //
    // GAP: part-07 …/03-states-and-pipelined-execution.md §8.3 — whether
    //      `NDArray(shape:scalarType:)` zeroes its storage on Apple platforms is
    //      undocumented (Python-side: on Linux it does NOT). The guide itself warns a
    //      single "it was zero" proves nothing (fresh kernel pages are zero-filled), so
    //      this probe dirties the allocator first: allocate a 0xAB-filled array of the
    //      same size, drop it, allocate uninitialized, scan for leftovers — repeatedly.
    // Candidates: (a) garbage observed → definitively NOT zeroed, keep the explicit
    //             zeroing advice as a correctness requirement; (b) always zero →
    //             still inconclusive-but-suggestive, keep the advice as cheap insurance.
    // Write-back: §8.3's GAP box, with the verdict wording above.
    func testNDArrayZeroInitialization() throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        let count = 8 * 1024 * 1024   // 8 MiB per array
        let rounds = 6
        var dirtyObserved = 0
        var nonzeroTotal = 0
        for _ in 0..<rounds {
            do {
                // Dirty a same-sized allocation, then drop it.
                let dirty = NDArray(scalars: repeatElement(UInt8(0xAB), count: count), shape: [count])
                _ = dirty
            }
            let fresh = NDArray(shape: [count], scalarType: .uint8)
            let nonzero = fresh.rawView().withUnsafeBytes { ptr, _, _ -> Int in
                let bytes = ptr.assumingMemoryBound(to: UInt8.self)
                var n = 0
                // Stride the scan; full scan of 8 MiB x 6 is still cheap, do it all.
                for i in 0..<count where bytes[i] != 0 { n += 1 }
                return n
            }
            if nonzero > 0 { dirtyObserved += 1 }
            nonzeroTotal += nonzero
        }
        Probe.result(
            "coreai.ndarray-zero-init",
            dirtyObserved > 0 ? "garbage-observed" : "all-zero-inconclusive",
            detail: "rounds=\(rounds) roundsWithGarbage=\(dirtyObserved) nonzeroBytesTotal=\(nonzeroTotal) \(Probe.runtimeDescription)"
        )
    }

    // MARK: coreai.cache-delete-while-referenced  [MAC-27 · DEVICE-27]
    //
    // GAP: notes/NEEDED-FROM-A-MACOS-27-MACHINE.md item 7 (first bullet) and
    //      part-07 …/02-specialization-caching-and-aot.md §7 — Apple's reference pages say
    //      deleting a referenced entry THROWS; the caching article says Core AI DEFERS
    //      deletion until the AIModel deallocates. Both cannot be true. Also §7's
    //      sub-question: does a deferred-deleted entry stop being findable by
    //      model(for:options:) immediately?
    // Candidates: (a) throws while referenced; (b) succeeds + defers (entry findable until
    //             dealloc); (c) succeeds + immediately unfindable.
    // Write-back: rewrite §7's contradiction box with the winner; update the
    //      retireModel(at:) recommendation if the throw arm never happens.
    func testCacheDeleteWhileReferenced() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        let url = try modelURLFromEnvironment()
        let options = SpecializationOptions.default

        var liveOutcome = "unknown"
        var findableAfterLiveDelete = "unknown"
        do {
            let model = try await AIModel(contentsOf: url, options: options)
            do {
                try AIModelCache.default.deleteEntries(for: url)
                liveOutcome = "succeeded"
            } catch {
                liveOutcome = "threw(\(type(of: error)): \(String(describing: error).prefix(200)))"
            }
            do {
                let found = try AIModelCache.default.model(for: url, options: options)
                findableAfterLiveDelete = found == nil ? "nil" : "non-nil"
            } catch {
                findableAfterLiveDelete = "lookup-threw(\(type(of: error)))"
            }
            _ = model // keep the reference alive through the delete above
        }
        // Reference now released. Re-specialize, then delete with no live reference.
        var releasedOutcome = "unknown"
        do {
            _ = try await AIModel.specialize(contentsOf: url, options: options)
            try AIModelCache.default.deleteEntries(for: url)
            releasedOutcome = "succeeded"
        } catch {
            releasedOutcome = "threw(\(type(of: error)))"
        }
        Probe.result(
            "coreai.cache-delete-while-referenced",
            "live=\(liveOutcome)",
            detail: "findableAfterLiveDelete=\(findableAfterLiveDelete) afterRelease=\(releasedOutcome) \(Probe.runtimeDescription)"
        )
    }

    // MARK: coreai.specialize-cancellation  [MAC-27 · DEVICE-27]
    //
    // GAP: part-07 …/02-specialization-caching-and-aot.md §5 and
    //      part-17 …/06-toolchain-and-asset-compatibility.md §5 — whether cancelling the
    //      enclosing Task actually stops specialization, and what state the cache is left
    //      in. Guide-named test: start specialize on a large model, cancel after ten
    //      seconds, check model(for:options:) and disk.
    // Candidates: (a) CancellationError promptly (cancellable); (b) runs to completion
    //             ignoring the cancel; (c) throws something else / corrupt entry.
    // Write-back: §5's "treat specialization as uncancellable" safe default — keep or
    //             replace with the measured contract.
    func testSpecializeCancellation() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        let url = try modelURLFromEnvironment()
        let options = SpecializationOptions.default
        try? AIModelCache.default.deleteEntries(for: url) // start cold

        let start = Date()
        let task = Task { () -> String in
            do {
                _ = try await AIModel.specialize(contentsOf: url, options: options)
                return "completed"
            } catch is CancellationError {
                return "threw-CancellationError"
            } catch {
                return "threw(\(type(of: error)))"
            }
        }
        try? await Task.sleep(for: .seconds(10))
        task.cancel()
        let outcome = await task.value
        let elapsed = Date().timeIntervalSince(start)
        var cacheState = "unknown"
        do {
            let found = try AIModelCache.default.model(for: url, options: options)
            cacheState = found == nil ? "no-entry" : "entry-present"
        } catch {
            cacheState = "lookup-threw(\(type(of: error)))"
        }
        Probe.result(
            "coreai.specialize-cancellation",
            outcome,
            detail: "elapsed=\(String(format: "%.1f", elapsed))s cacheAfter=\(cacheState) \(Probe.runtimeDescription)"
        )
    }

    // MARK: coreai.cache-location-size  [MAC-27 · DEVICE-27]
    //
    // GAP: part-07 …/02-specialization-caching-and-aot.md §6 — where AIModelCache.default
    //      lives on disk and how big an entry is: no size API, no documented location, no
    //      enumeration. Guide-named test: measure the container before and after a
    //      specialization, then inspect for the directory.
    // Candidates: app container Caches / a system-managed store outside the sandbox.
    // Write-back: §6's GAP box — the observed directory (if visible) and the growth-vs-
    //      source-asset ratio.
    func testCacheLocationAndSize() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        let url = try modelURLFromEnvironment()
        let options = SpecializationOptions.default
        try? AIModelCache.default.deleteEntries(for: url)

        func directorySize(_ dir: URL) -> Int64 {
            guard let e = FileManager.default.enumerator(at: dir, includingPropertiesForKeys: [.totalFileAllocatedSizeKey], options: [.skipsHiddenFiles], errorHandler: { _, _ in true }) else { return 0 }
            var total: Int64 = 0
            for case let f as URL in e {
                total += Int64((try? f.resourceValues(forKeys: [.totalFileAllocatedSizeKey]).totalFileAllocatedSize) ?? 0)
            }
            return total
        }
        let caches = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let sourceSize = directorySize(url)

        let cachesBefore = directorySize(caches)
        let supportBefore = directorySize(appSupport)
        let started = Date()
        _ = try await AIModel.specialize(contentsOf: url, options: options)
        let took = Date().timeIntervalSince(started)
        let cachesAfter = directorySize(caches)
        let supportAfter = directorySize(appSupport)

        // Newest entries under Caches, as location candidates.
        let newest = (try? FileManager.default.contentsOfDirectory(at: caches, includingPropertiesForKeys: [.contentModificationDateKey]))?
            .filter { ((try? $0.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast) > started }
            .map(\.lastPathComponent) ?? []

        Probe.result(
            "coreai.cache-location-size",
            "cachesGrowth=\(cachesAfter - cachesBefore) appSupportGrowth=\(supportAfter - supportBefore)",
            detail: "sourceAsset=\(sourceSize)B specializeTook=\(String(format: "%.1f", took))s newCacheEntries=\(newest) \(Probe.runtimeDescription)"
        )
    }

    // MARK: coreai.specialize-return-identity  [MAC-27 · DEVICE-27]
    //
    // GAP: part-07 …/02-specialization-caching-and-aot.md §9 (app-group discussion) — is
    //      the AIModel RETURNED by specialize(…, cache:…) backed by the same cache entry
    //      the subsequent model(for:options:) lookup returns? Apple always demonstrates
    //      the two-step and never uses specialize's return value. Compare bookmarkData.
    //      (The app-group variant needs a signed host with the app-group entitlement — a
    //      plain SwiftPM test has none, so this runs the default-cache half; the group
    //      half is listed under SKIPPED in the README.)
    // Candidates: (a) same entry (bookmarkData equal) → one-step load is safe;
    //             (b) different → keep Apple's two-step.
    // Write-back: §9's GAP box, default-cache sentence.
    func testSpecializeReturnIdentity() async throws {
        guard #available(macOS 27.0, iOS 27.0, *) else { throw XCTSkip("SKIPPED: needs OS 27") }
        let url = try modelURLFromEnvironment()
        let options = SpecializationOptions.default
        let returned = try await AIModel.specialize(contentsOf: url, options: options)
        let lookedUp = try AIModelCache.default.model(for: url, options: options)
        guard let lookedUp else {
            Probe.result("coreai.specialize-return-identity", "lookup-nil",
                         detail: "specialize returned a model but model(for:options:) found no entry \(Probe.runtimeDescription)")
            return
        }
        let same = returned.bookmarkData == lookedUp.bookmarkData
        Probe.result(
            "coreai.specialize-return-identity",
            same ? "same-entry" : "different-entry",
            detail: "returnedBookmarkBytes=\(returned.bookmarkData.count) lookedUpBookmarkBytes=\(lookedUp.bookmarkData.count) \(Probe.runtimeDescription)"
        )
    }
}
#endif
