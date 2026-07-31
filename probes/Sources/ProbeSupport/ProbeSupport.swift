// ProbeSupport — shared plumbing for the runtime probes.
//
// A probe never fakes a pass/fail. A probe that MEASURES prints a structured
//     PROBE-RESULT name=<gap-id> value=<...>
// line and passes; a probe that OBSERVES one of several documented-contradictory
// behaviors asserts nothing and prints which branch happened. The test log is
// the artifact; harvest every PROBE-RESULT line back into the guides.

import Foundation

public enum Probe {
    /// Emit a harvestable result line. `value` should be short and greppable;
    /// use `detail` for free-form context (error strings, dumps).
    @discardableResult
    public static func result(_ name: String, _ value: String, detail: String? = nil) -> String {
        var line = "PROBE-RESULT name=\(name) value=\(value)"
        if let detail { line += " detail=\(detail.replacingOccurrences(of: "\n", with: "⏎"))" }
        print(line)
        // fflush so results survive a later crash of the test process.
        fflush(stdout)
        return line
    }

    /// Environment knob (e.g. PROBE_AIMODEL_URL, PROBE_ENUM_RUNS).
    public static func env(_ key: String) -> String? {
        ProcessInfo.processInfo.environment[key]
    }

    /// "macOS 26.5.2 (25F84)" / "iOS 27.0 …" plus simulator marker — stamped into
    /// every result so a harvested line is self-describing.
    public static var runtimeDescription: String {
        let v = ProcessInfo.processInfo.operatingSystemVersion
        var s = "os=\(v.majorVersion).\(v.minorVersion).\(v.patchVersion)"
        #if targetEnvironment(simulator)
        s += "-simulator"
        #endif
        #if os(macOS)
        s += " platform=macOS"
        #elseif os(iOS)
        s += " platform=iOS"
        #endif
        return s
    }

    /// Thread-safe call counter for probe fixtures (tools, session providers)
    /// that need to record "did I run, and how often" across concurrency domains.
    public final class Counter: @unchecked Sendable {
        private let lock = NSLock()
        private var _count = 0
        public init() {}
        public var count: Int { lock.withLock { _count } }
        public func increment() { lock.withLock { _count += 1 } }
    }

    /// Race an async operation against a wall-clock bound. Returns nil on timeout.
    /// Used so a hung model call degrades to a recorded timeout instead of a hung
    /// test run.
    public static func withTimeout<T: Sendable>(
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
}
