#!/usr/bin/env python3
"""Type-check SDK gates and platform policies without executing model-backed code."""
import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'artifacts/repair-review-findings/compat-cache'


def command(argv, source=None):
    result = subprocess.run(argv, input=source, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def main():
    swiftc = command(['xcrun', '--find', 'swiftc'])
    checks = []
    macos = command(['xcrun', '--sdk', 'macosx', '--show-sdk-path'])
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        consumer = '''import CompatibilityFixture
#if canImport(CompatibilityFixture, _version: 2.1)
let value = AddedInNewSDK()
#else
let value = Legacy()
#endif
'''
        for version in ('2.0.68', '2.1.14'):
            output = root / version;output.mkdir()
            source = 'public struct Legacy { public init() {} }\n'
            if version.startswith('2.1'):
                source += 'public struct AddedInNewSDK { public init() {} }\n'
            command([swiftc, '-sdk', macos, '-target', 'arm64-apple-macos27.0', '-emit-module', '-module-name', 'CompatibilityFixture', '-user-module-version', version,
                     '-module-cache-path', str(CACHE), '-emit-module-path', str(output / 'CompatibilityFixture.swiftmodule'), '-'], source)
            command([swiftc, '-sdk', macos, '-target', 'arm64-apple-macos27.0', '-typecheck', '-I', str(output), '-module-cache-path', str(CACHE), '-'], consumer)
            checks.append({'check': 'controlled-module-version-gate', 'version': version, 'status': 'passed'})
    data = '''import FoundationModels
import UniformTypeIdentifiers
enum TranslationError: Error { case unsupported }
@available(macOS 27.0, *)
func translate(_ entry: Transcript.Entry) throws {
 switch entry {
 case .instructions, .prompt, .toolCalls, .toolOutput, .response, .reasoning: break
 #if canImport(FoundationModels, _version: 2.1)
 case .data: throw TranslationError.unsupported
 #endif
 @unknown default: throw TranslationError.unsupported
 }
}
#if canImport(FoundationModels, _version: 2.1)
@available(macOS 27.2, *)
func supportsData(_ model: any LanguageModel) async throws -> Bool {
 let entries = try await model.supportsDataEntryType(UTType.data)
 let attachments = try await model.supportsDataAttachmentType(UTType.data)
 return entries && attachments
}
#endif
'''
    command([swiftc, '-typecheck', '-swift-version', '6', '-sdk', macos, '-target', 'arm64-apple-macos27.0', '-module-cache-path', str(CACHE), '-'], data)
    checks.append({'check': 'data-translation-and-capability-gates', 'status': 'passed', 'runtimeExecution': False})
    policy = '''import CoreAI
@available(macOS 27.0, tvOS 27.0, *)
func policy() -> AIModelCache.Policy {
 #if os(tvOS)
 return .default
 #else
 return .persistent
 #endif
}
'''
    command([swiftc, '-typecheck', '-sdk', macos, '-target', 'arm64-apple-macos27.0', '-module-cache-path', str(CACHE), '-'], policy)
    checks.append({'check': 'cache-policy-macos', 'status': 'passed'})
    tvos = subprocess.run(['xcrun', '--sdk', 'appletvos', '--show-sdk-path'], text=True, capture_output=True)
    if tvos.returncode:
        checks.append({'check': 'cache-policy-tvos', 'status': 'unavailable', 'reason': tvos.stderr.strip()})
    else:
        command([swiftc, '-typecheck', '-sdk', tvos.stdout.strip(), '-target', 'arm64-apple-tvos27.0', '-module-cache-path', str(CACHE), '-'], policy)
        checks.append({'check': 'cache-policy-tvos', 'status': 'passed'})
    sdks = {'macosx': {key: command(['xcrun', '--sdk', 'macosx', flag]) for key, flag in [('version', '--show-sdk-version'), ('build', '--show-sdk-build-version')]}}
    if tvos.returncode == 0:
        sdks['appletvos'] = {key: command(['xcrun', '--sdk', 'appletvos', flag]) for key, flag in [('version', '--show-sdk-version'), ('build', '--show-sdk-build-version')]}
    print(json.dumps({'checks': checks, 'sdks': sdks, 'runtimeExecution': False}, indent=2))


if __name__ == '__main__':
    main()
