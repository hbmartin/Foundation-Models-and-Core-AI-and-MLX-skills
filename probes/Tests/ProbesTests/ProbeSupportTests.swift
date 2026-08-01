import Foundation
import ProbeSupport
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
        let ran = Probe.Counter()
        let task = Task {
            await Task.yield()
            return try await Probe.withTimeout(seconds: 30) { () async throws -> Int in
                try await Task.sleep(for: .seconds(30))
                ran.increment()
                return 1
            }
        }
        task.cancel()
        do {
            _ = try await task.value
            XCTFail("expected parent cancellation")
        } catch is CancellationError {
            // Expected.
        } catch {
            XCTFail("unexpected error: \(error)")
        }
        XCTAssertEqual(ran.count, 0)
    }

    func testParentCancellationCancelsBothRacers() async {
        let operationCancelled = expectation(description: "operation cancelled")
        let task = Task {
            try await Probe.withTimeout(seconds: 30) {
                do {
                    try await Task.sleep(for: .seconds(30))
                    return 1
                } catch is CancellationError {
                    operationCancelled.fulfill()
                    throw CancellationError()
                }
            }
        }
        await Task.yield()
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
