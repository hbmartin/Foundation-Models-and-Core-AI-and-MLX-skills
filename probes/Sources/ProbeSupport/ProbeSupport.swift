// ProbeSupport — shared plumbing for the runtime probes.
//
// A probe never fakes a pass/fail. A probe that MEASURES prints a structured
//     PROBE-RESULT name=<gap-id> value=<...>
// line and passes; a probe that OBSERVES one of several documented-contradictory
// behaviors asserts nothing and prints which branch happened. The test log is
// the artifact; harvest every PROBE-RESULT line back into the guides.

import Foundation

public enum Probe {
    public enum TimeoutResult<T: Sendable>: Sendable {
        case value(T)
        case timedOut
    }

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

    /// Numeric environment knob. A supplied value that fails to parse is
    /// narrated before falling back, so a typo never silently reverts a run
    /// to its default duration.
    public static func envSeconds(_ key: String, default defaultValue: Double) -> Double {
        guard let raw = env(key) else { return defaultValue }
        guard let parsed = Double(raw), parsed.isFinite else {
            print("workload-env warning name=\(key) raw=\"\(raw)\" using-default=\(defaultValue)")
            fflush(stdout)
            return defaultValue
        }
        return max(0, parsed)
    }

    /// Integer variant of `envSeconds(_:default:)` with the same narration.
    public static func envCount(_ key: String, default defaultValue: Int) -> Int {
        guard let raw = env(key) else { return defaultValue }
        guard let parsed = Int(raw) else {
            print("workload-env warning name=\(key) raw=\"\(raw)\" using-default=\(defaultValue)")
            fflush(stdout)
            return defaultValue
        }
        return max(0, parsed)
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

    /// Race an async operation against a wall-clock bound without waiting for a
    /// cancelled operation that ignores cancellation. Operation errors and parent
    /// cancellation propagate; timeout is a distinct, non-error result.
    /// Cancellation or timeout before operation admission prevents the operation
    /// from starting. Once admitted, the operation must cooperate with cancellation.
    public static func withTimeout<T: Sendable>(
        seconds: Double,
        _ op: @escaping @Sendable () async throws -> T
    ) async throws -> TimeoutResult<T> {
        try Task.checkCancellation()
        let race = TimeoutRace<T>()
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                race.start(continuation: continuation, seconds: seconds, operation: op)
            }
        } onCancel: {
            race.cancel()
        }
    }
}

final class TimeoutRace<T: Sendable>: @unchecked Sendable {
    enum Winner { case operation, timer }
    typealias TaskFactory = @Sendable (Winner, @escaping @Sendable () async -> Void) -> Task<Void, Never>

    private let lock = NSLock()
    private let makeTask: TaskFactory
    private var continuation: CheckedContinuation<Probe.TimeoutResult<T>, any Error>?
    private var terminal: Result<Probe.TimeoutResult<T>, any Error>?
    private var operationTask: Task<Void, Never>?
    private var timerTask: Task<Void, Never>?
    private var operationAdmitted = false

    // Instance-local scheduling seam for deterministic race tests. Factories must
    // return a scheduled task without synchronously invoking its body or this race.
    init(makeTask: @escaping TaskFactory = { _, body in Task { await body() } }) {
        self.makeTask = makeTask
    }

    func start(continuation newContinuation: CheckedContinuation<Probe.TimeoutResult<T>, any Error>,
               seconds: Double, operation: @escaping @Sendable () async throws -> T) {
        lock.lock()
        if let terminal {
            lock.unlock()
            newContinuation.resume(with: terminal)
            return
        }

        continuation = newContinuation
        operationTask = makeTask(.operation) {
            guard self.admitOperation() else { return }
            do {
                self.finish(.success(.value(try await operation())), winner: .operation)
            } catch {
                self.finish(.failure(error), winner: .operation)
            }
        }
        timerTask = makeTask(.timer) {
            do {
                try await Task.sleep(for: .seconds(max(0, seconds)))
            } catch {
                return
            }
            self.finish(.success(.timedOut), winner: .timer)
        }
        // Both handles are installed before cancellation/completion can settle.
        lock.unlock()
    }

    private func admitOperation() -> Bool {
        lock.withLock {
            guard terminal == nil, !operationAdmitted else { return false }
            operationAdmitted = true
            return true
        }
    }

    func finish(_ result: Result<Probe.TimeoutResult<T>, any Error>, winner: Winner?) {
        let continuationToResume: CheckedContinuation<Probe.TimeoutResult<T>, any Error>?
        let tasksToCancel: [Task<Void, Never>]
        lock.lock()
        guard terminal == nil else {
            lock.unlock()
            return
        }
        terminal = result
        continuationToResume = continuation
        continuation = nil
        switch winner {
        case .operation:
            tasksToCancel = [timerTask].compactMap { $0 }
        case .timer:
            tasksToCancel = [operationTask].compactMap { $0 }
        case nil:
            tasksToCancel = [operationTask, timerTask].compactMap { $0 }
        }
        operationTask = nil
        timerTask = nil
        lock.unlock()

        for task in tasksToCancel { task.cancel() }
        continuationToResume?.resume(with: result)
    }

    func cancel() {
        finish(.failure(CancellationError()), winner: nil)
    }
}
