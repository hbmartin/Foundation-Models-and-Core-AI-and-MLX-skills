import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/verify-sdk-compatibility.py'
spec = importlib.util.spec_from_file_location('sdk_compatibility_tests', SCRIPT)
compatibility = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compatibility)


class CompatibilityTests(unittest.TestCase):
    def test_negative_controls_require_the_expected_compile_failure(self):
        for code, diagnostics in ((0, ''), (1, 'compiler infrastructure failure')):
            with self.subTest(code=code), mock.patch.object(compatibility.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], code, '', diagnostics)):
                with self.assertRaisesRegex(RuntimeError, 'negative control'):
                    compatibility.command(['swiftc'], expected_error="cannot find 'Legacy'")

    def test_module_metadata_controls_expected_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            module = root / 'System/Library/Frameworks/FoundationModels.framework/Modules/FoundationModels.swiftmodule'
            module.mkdir(parents=True)
            interface = module / 'arm64e-apple-macos.swiftinterface'
            for version, expected in (('2.0.68', False), ('2.1.14', True)):
                interface.write_text(f'// swift-module-flags: -user-module-version {version}\n')
                self.assertEqual(compatibility.foundation_metadata(root), (version, expected))
            interface.write_text('// missing module version\n')
            with self.assertRaisesRegex(RuntimeError, 'module version'):
                compatibility.foundation_metadata(root)

    @unittest.skipUnless(sys.platform == 'darwin' and shutil.which('xcrun'), 'requires an Apple SDK')
    def test_native_typechecks_reject_incorrect_branches(self):
        version = subprocess.run(['xcrun', '--sdk', 'macosx', '--show-sdk-version'], capture_output=True, text=True)
        if version.returncode or int(version.stdout.split('.')[0]) < 27:
            self.skipTest('requires SDK 27 or later')
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        controls = [c for c in report['checks'] if c['check'] in
                    ('controlled-module-version-gate', 'data-translation-and-capability-gates')]
        self.assertEqual(len(controls), 3)
        self.assertTrue(all(c['status'] == 'passed' and c['incorrectBranchRejected'] for c in controls))
        self.assertFalse(report['runtimeExecution'])
        self.assertTrue(report['compiler'])
