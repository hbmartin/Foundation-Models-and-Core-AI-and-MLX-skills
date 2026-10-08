import Foundation
@testable import ProbeSupport
import XCTest

final class ProbeSupportTests: XCTestCase {
    private struct ExpectedError: Error {}

    func testTimeoutPreservesSuccessfulValue() async throws {
        let result = try await Probe.withTimeout(seconds: 1) { 42 }
        switch result {
        case .value(let value):
            XCTAssertEqual(value, 42)
        case .timedOut:
            XCTFail("successful operation timed out")
        }
    }

    func testTimeoutPreservesOperationError() async {
        do {
            _ = try await Probe.withTimeout(seconds: 1) { () async throws -> Int in
                throw ExpectedError()
            }
            XCTFail("expected operation error")
        } catch is ExpectedError {
            // Expected.
        } catch {
            XCTFail("unexpected error: \(error)")
        }
    }

    func testTimeoutReturnsPromptlyWhenOperationIgnoresCancellation() async throws {
        let started = ContinuousClock.now
        let result = try await Probe.withTimeout(seconds: 0.05) {
            let end = ContinuousClock.now.advanced(by: .milliseconds(500))
            while ContinuousClock.now < end {
                await Task.yield()
            }
            return 1
        }
        let elapsed = started.duration(to: .now)
        if case .value = result { XCTFail("expected timeout") }
        // Generous headroom for loaded CI hosts, but still below the 500 ms
        // spin: passing proves the call returned at the timeout, not the op.
        XCTAssertLessThan(elapsed, .milliseconds(450))
    }

    func testOperationErrorAfterTimeoutIsSwallowed() async throws {
        let result = try await Probe.withTimeout(seconds: 0.05) { () async throws -> Int in
            // try? survives the cancellation from the timer's win; the late
            // throw below must be dropped by the settled race, not surfaced.
            try? await Task.sleep(for: .milliseconds(200))
            throw ExpectedError()
        }
        if case .value = result { XCTFail("expected timeout") }
    }

    func testNearSimultaneousCompletionResolvesToExactlyOneOutcome() async throws {
        // Race the timer and the operation at the same nominal deadline many
        // times; a double resume of the checked continuation would crash.
        for _ in 0..<50 {
            let result = try await Probe.withTimeout(seconds: 0.01) { () async throws -> Int in
                try? await Task.sleep(for: .milliseconds(10))
                return 1
            }
            switch result {
            case .value(let value): XCTAssertEqual(value, 1)
            case .timedOut: break
            }
        }
    }

    func testParentCancelledBeforeEntryDoesNotStartWork() async {
        let operationRan = expectation(description: "operation must not run")
        operationRan.isInverted = true
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try await Probe.withTimeout(seconds: 30) { () async throws -> Int in
                operationRan.fulfill()
                return 1
            }
        }
        do {
            _ = try await task.value
            XCTFail("expected parent cancellation")
        } catch is CancellationError {
            // Expected.
        } catch {
            XCTFail("unexpected error: \(error)")
        }
        await fulfillment(of: [operationRan], timeout: 0.1)
    }

    func testCancellationBeforeRegistrationDoesNotCreateRacers() async {
        let created = Probe.Counter()
        let ran = Probe.Counter()
        let race = TimeoutRace<Int>(makeTask: { _, body in
            created.increment()
            return Task { await body() }
        })
        // Simulate cancellation after the entry check but before registration.
        race.cancel()
        do {
            _ = try await withCheckedThrowingContinuation { continuation in
                race.start(continuation: continuation, seconds: 30) {
                    ran.increment()
                    return 1
                }
            }
            XCTFail("expected cancellation")
        } catch is CancellationError {
            // Expected.
        } catch {
            XCTFail("unexpected error: \(error)")
        }
        XCTAssertEqual(created.count, 0)
        XCTAssertEqual(ran.count, 0)
    }

    func testCancellationBeforeAdmissionDoesNotStartWork() async {
        await verifySettledRacePreventsAdmission(cancel: true)
    }

    func testTimeoutBeforeAdmissionDoesNotStartWork() async {
        await verifySettledRacePreventsAdmission(cancel: false)
    }

    private func verifySettledRacePreventsAdmission(cancel: Bool) async {
        let operationQueued = expectation(description: "operation queued before admission")
        let operationExited = expectation(description: "operation racer exited")
        let timerExited = expectation(description: "timer racer exited")
        let gate = SuspensionGate()
        let ran = Probe.Counter()
        let race = TimeoutRace<Int>(makeTask: { winner, body in
            Task {
                switch winner {
                case .operation:
                    operationQueued.fulfill()
                    await gate.wait()
                    await body()
                    operationExited.fulfill()
                case .timer:
                    await body()
                    timerExited.fulfill()
                }
            }
        })
        let task = Task {
            try await withTaskCancellationHandler {
                try await withCheckedThrowingContinuation { continuation in
                    race.start(continuation: continuation, seconds: cancel ? 30 : 0) {
                        ran.increment()
                        return 1
                    }
                }
            } onCancel: {
                race.cancel()
            }
        }
        await fulfillment(of: [operationQueued], timeout: 1)
        if cancel { task.cancel() }
        do {
            let result = try await task.value
            if cancel { XCTFail("expected cancellation") }
            if case .value = result { XCTFail("expected timeout") }
        } catch is CancellationError {
            if !cancel { XCTFail("unexpected cancellation") }
        } catch {
            XCTFail("unexpected error: \(error)")
        }
        await gate.open()
        // Join both racers before asserting: the old immediate assertion could
        // pass while the unstructured operation task had not yet been scheduled.
        await fulfillment(of: [operationExited, timerExited], timeout: 1)
        XCTAssertEqual(ran.count, 0)
    }

    func testParentCancellationCancelsBothRacers() async {
        let operationStarted = expectation(description: "operation started")
        let operationCancelled = expectation(description: "operation cancelled")
        let task = Task {
            try await Probe.withTimeout(seconds: 30) {
                operationStarted.fulfill()
                do {
                    try await Task.sleep(for: .seconds(30))
                    return 1
                } catch is CancellationError {
                    operationCancelled.fulfill()
                    throw CancellationError()
                }
            }
        }
        await fulfillment(of: [operationStarted], timeout: 1)
        task.cancel()
        do {
            _ = try await task.value
            XCTFail("expected parent cancellation")
        } catch is CancellationError {
            // Expected.
        } catch {
            XCTFail("unexpected error: \(error)")
        }
        await fulfillment(of: [operationCancelled], timeout: 1)
    }
}

private actor SuspensionGate {
    private var isOpen = false
    private var continuation: CheckedContinuation<Void, Never>?

    func wait() async {
        if isOpen { return }
        await withCheckedContinuation { continuation in
            self.continuation = continuation
        }
    }

    func open() {
        isOpen = true
        continuation?.resume()
        continuation = nil
    }
}
