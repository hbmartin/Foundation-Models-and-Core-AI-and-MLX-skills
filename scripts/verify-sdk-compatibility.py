#!/usr/bin/env python3
"""Type-check SDK gates and platform policies without executing model-backed code."""
import json
import pathlib
import re
import subprocess
import tempfile
import datetime as dt

FIXTURE_GATE = 'canImport(CompatibilityFixture, _version: 2.1)'
FOUNDATION_GATE = 'canImport(FoundationModels, _version: 2.1)'


def command(argv, source=None, expected_error=None):
    result = subprocess.run(argv, input=source, text=True, capture_output=True, timeout=60)
    if expected_error is not None:
        if not result.returncode or expected_error not in result.stderr:
            raise RuntimeError(f'negative control did not reject {expected_error}: {result.stderr}')
        return result.stderr.strip()
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def fixture_consumer(condition=FIXTURE_GATE):
    return f'''import CompatibilityFixture
#if {condition}
let value = AddedInNewSDK()
#else
let value = Legacy()
#endif
'''


def controlled_gate_checks(swiftc, sdk, root):
    checks = []
    common = [swiftc, '-sdk', sdk, '-target', 'arm64-apple-macos27.0', '-warnings-as-errors',
              '-module-cache-path', str(root / 'cache')]
    for version, symbol, incorrect_condition, missing in (
            ('2.0.68', 'Legacy', 'true', 'AddedInNewSDK'),
            ('2.1.14', 'AddedInNewSDK', 'false', 'Legacy')):
        output = root / version
        output.mkdir()
        source = f'public struct {symbol} {{ public init() {{}} }}\n'
        command([*common, '-emit-module', '-module-name', 'CompatibilityFixture', '-user-module-version', version,
                 '-emit-module-path', str(output / 'CompatibilityFixture.swiftmodule'), '-'], source)
        consumer_command = [*common, '-typecheck', '-I', str(output), '-']
        command(consumer_command, fixture_consumer())
        command(consumer_command, fixture_consumer(incorrect_condition), expected_error=f"cannot find '{missing}'")
        checks.append({'check': 'controlled-module-version-gate', 'version': version, 'status': 'passed',
                       'expectedSymbol': symbol, 'incorrectBranchRejected': True})
    return checks


DATA_API = '''import FoundationModels
import UniformTypeIdentifiers
@available(macOS 27.2, *)
func supportsData(_ model: any LanguageModel) async throws -> Bool {
 let entries = try await model.supportsDataEntryType(UTType.data)
 let attachments = try await model.supportsDataAttachmentType(UTType.data)
 return entries && attachments
}
'''


def foundation_source(has_data, condition=FOUNDATION_GATE):
    expected = 'NewSDK' if has_data else 'OldSDK'
    return f'''import FoundationModels
import UniformTypeIdentifiers
struct {expected} {{}}
#if {condition}
let selectedBranch: {expected} = NewSDK()
#else
let selectedBranch: {expected} = OldSDK()
#endif
''' + '''
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
'''.replace(FOUNDATION_GATE, condition)


def foundation_metadata(sdk):
    directory = pathlib.Path(sdk) / 'System/Library/Frameworks/FoundationModels.framework/Modules/FoundationModels.swiftmodule'
    versions = set()
    for path in directory.glob('arm64*-apple-macos.swiftinterface'):
        match = re.search(r'-user-module-version (\d+(?:\.\d+)+)', path.read_text())
        if match:
            versions.add(match[1])
    if len(versions) != 1:
        raise RuntimeError('cannot establish the FoundationModels module version from the target SDK')
    version = versions.pop()
    return version, tuple(map(int, version.split('.')[:2])) >= (2, 1)


def verify(swiftc, macos, root):
    checks = controlled_gate_checks(swiftc, macos, root)
    version, has_data = foundation_metadata(macos)
    common = [swiftc, '-typecheck', '-swift-version', '6', '-warnings-as-errors', '-sdk', macos,
              '-target', 'arm64-apple-macos27.0', '-module-cache-path', str(root / 'cache')]
    command([*common, '-'], foundation_source(has_data))
    command([*common, '-'], foundation_source(has_data, 'false' if has_data else 'true'),
            expected_error="cannot find 'OldSDK'" if has_data else "cannot find 'NewSDK'")
    if has_data:
        command([*common, '-'], DATA_API)
    checks.append({'check': 'data-translation-and-capability-gates', 'status': 'passed', 'runtimeExecution': False,
                   'moduleVersion': version, 'expectedBranch': 'new' if has_data else 'legacy',
                   'incorrectBranchRejected': True, 'ungatedDataAPIsChecked': has_data})
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
    command([*common, '-'], policy)
    checks.append({'check': 'cache-policy-macos', 'status': 'passed'})
    tvos = subprocess.run(['xcrun', '--sdk', 'appletvos', '--show-sdk-path'], text=True, capture_output=True)
    if tvos.returncode:
        checks.append({'check': 'cache-policy-tvos', 'status': 'unavailable', 'reason': tvos.stderr.strip()})
    else:
        command([swiftc, '-typecheck', '-warnings-as-errors', '-sdk', tvos.stdout.strip(), '-target', 'arm64-apple-tvos27.0', '-module-cache-path', str(root / 'cache'), '-'], policy)
        checks.append({'check': 'cache-policy-tvos', 'status': 'passed'})
    sdks = {'macosx': {key: command(['xcrun', '--sdk', 'macosx', flag]) for key, flag in [('version', '--show-sdk-version'), ('build', '--show-sdk-build-version')]}}
    if tvos.returncode == 0:
        sdks['appletvos'] = {key: command(['xcrun', '--sdk', 'appletvos', flag]) for key, flag in [('version', '--show-sdk-version'), ('build', '--show-sdk-build-version')]}
    return {'schemaVersion': 2, 'checkedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
            'compiler': command([swiftc, '--version']), 'target': 'arm64-apple-macos27.0',
            'checks': checks, 'sdks': sdks, 'runtimeExecution': False}


def main():
    swiftc = command(['xcrun', '--find', 'swiftc'])
    macos = command(['xcrun', '--sdk', 'macosx', '--show-sdk-path'])
    with tempfile.TemporaryDirectory() as directory:
        result = verify(swiftc, macos, pathlib.Path(directory))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
