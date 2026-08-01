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
        XCTAssertLessThan(elapsed, .milliseconds(300))
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
