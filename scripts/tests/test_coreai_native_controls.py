"""Portable checks for native recording and selected guide contracts; no SDK imports."""
import ast
import asyncio
from contextlib import nullcontext
import importlib.metadata
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from scripts.coreai_examples import guide_examples
from scripts import verify_coreai_examples as verifier

ROOT = Path(__file__).resolve().parents[2]


def guide_function(example_id, name, namespace):
    example = next(e for e in guide_examples(ROOT) if e.id == example_id)
    node = next(n for n in ast.parse(example.code).body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(example.path), "exec"), namespace)
    return namespace[name]


class NativeRecordingTests(unittest.TestCase):
    def run_setup(self, *, compression=False, missing=None, command_failure=None):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'record.json'
            argv = ['verifier', '--source-repo', '/unused', '--reviewed-revision', 'a' * 40,
                    '--out', str(output)] + (['--compression'] if compression else [])
            names = ['state-protocol', 'shipped-asset-gate', 'ci-asset-gate',
                     'compression-native-fixtures', 'composite-quantization']
            blobs = dict.fromkeys(('scripts/verify_coreai_examples.py',
                                  'scripts/coreai_examples.py', 'scripts/mdlinks.py'), b'fixture')
            queried = []

            def version(name):
                queried.append(name)
                if name == missing:
                    raise importlib.metadata.PackageNotFoundError(name)
                return 'fixture-version'

            def command(args, **kwargs):
                if args[0] == command_failure:
                    raise subprocess.CalledProcessError(1, args)
                return 'fixture-toolchain\n'

            real_import = __import__

            def stop_native_import(name, *args, **kwargs):
                if name == 'numpy':
                    raise RuntimeError('portable test stops before native execution')
                return real_import(name, *args, **kwargs)

            with mock.patch.object(sys, 'argv', argv), \
                    mock.patch.object(verifier, 'approved_snapshots', return_value=('b' * 40, blobs, {})), \
                    mock.patch.object(verifier, 'load_trusted_reader'), \
                    mock.patch.object(verifier, 'snapshot_examples', return_value=dict.fromkeys(names)), \
                    mock.patch.object(verifier.platform, 'platform', return_value='fixture-os'), \
                    mock.patch.object(verifier.importlib.metadata, 'version', side_effect=version), \
                    mock.patch.object(verifier.subprocess, 'check_output', side_effect=command), \
                    mock.patch('builtins.__import__', side_effect=stop_native_import):
                status = verifier.main()
            self.assertEqual(status, 1)
            record = json.loads(output.read_text())
            self.assertEqual(record['source_revision'], 'a' * 40)
            self.assertEqual(record['fixtures'][-1]['outcome'], 'FAIL')
            return record, queried

    def test_migration_only_does_not_query_compression_packages(self):
        record, queried = self.run_setup(missing='coreai-opt')
        self.assertEqual(queried, ['torch', 'coreai-core', 'coreai-torch', 'numpy'])
        self.assertFalse(record['compression'])
        self.assertIn('stops before native execution', record['fixtures'][-1]['details'])

    def test_missing_required_package_is_recorded(self):
        for compression, missing in ((False, 'coreai-core'), (True, 'coreai-opt'), (True, 'scikit-learn')):
            with self.subTest(compression=compression, missing=missing):
                record, _ = self.run_setup(compression=compression, missing=missing)
                self.assertIn('PackageNotFoundError', record['fixtures'][-1]['details'])
                self.assertNotIn(missing, record['packages'])

    def test_toolchain_failures_are_recorded(self):
        for command in ('sw_vers', 'xcode-select', 'xcodebuild', 'xcrun'):
            with self.subTest(command=command), mock.patch.dict('os.environ', {'DEVELOPER_DIR': ''}):
                record, _ = self.run_setup(command_failure=command)
                self.assertIn(command, record['fixtures'][-1]['details'])

    def test_negative_controls_require_exception_and_diagnostic(self):
        def fail(error):
            raise error
        expected = (ValueError, 'outside declared range')
        good = verifier.fixture_result('range', lambda: fail(ValueError('outside declared range')), expected)
        self.assertEqual(good['outcome'], 'PASS (rejected)')
        for fn in (lambda: None, lambda: fail(RuntimeError('outside declared range')),
                   lambda: fail(ValueError('asset loader failed')), lambda: fail(AssertionError('unrelated'))):
            self.assertEqual(verifier.fixture_result('range', fn, expected)['outcome'], 'FAIL')

    def test_range_validation_survives_optimized_python_before_asset_load(self):
        script = '''
import ast,asyncio,json
from pathlib import Path
from scripts.coreai_examples import guide_examples
e=next(e for e in guide_examples(Path('.')) if e.id=='state-protocol')
node=next(n for n in ast.parse(e.code).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='verify_state_asset')
ns={}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(e.path),'exec'),ns)
for lengths in ((1,),(33,),(2,1),iter((2,33))):
 try: asyncio.run(ns['verify_state_asset']('/must-not-load',None,lengths=lengths))
 except ValueError as error:
  if str(error)!='sequence outside declared range 2–32': raise
 else: raise RuntimeError('range validation disappeared')
print(json.dumps({'rejected_before_any_model_or_asset_access':True}))
'''
        result = subprocess.run([sys.executable, '-O', '-c', script], cwd=ROOT,
                                capture_output=True, text=True, check=True, timeout=10)
        self.assertTrue(json.loads(result.stdout)['rejected_before_any_model_or_asset_access'])


class CIGuideContractTests(unittest.TestCase):
    def make_gate(self, ir):
        class Array:
            valid = True
            @property
            def shape(self):
                if not self.valid:
                    raise RuntimeError('borrowed output expired')
                return (1, 2)
            def copy(self):
                self.shape
                return Array()

        class Tensor:
            def __init__(self, array=None):
                self.array = array or Array()
            def detach(self): return self
            def cpu(self): return self
            def numpy(self): return self.array

        class Model:
            training = False
            def __call__(self, *args): return Tensor()

        borrowed = Array()
        async def infer(**kwargs): return {'y': Tensor(borrowed)}
        class Function:
            desc = SimpleNamespace(input_names=['x'], output_names=['y'], state_names=[])
            async def __call__(self, **kwargs): return await infer(**kwargs)
        class Executable:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): borrowed.valid = False
            def load_function(self, name): return Function()
        asset = SimpleNamespace(program=ir, executable=Executable)
        loader = mock.Mock(return_value=asset)
        ns = {'Path': Path, 'torch': SimpleNamespace(no_grad=nullcontext), 'NDArray': lambda x: x,
              'AIModelAsset': SimpleNamespace(load=loader),
              'np': SimpleNamespace(isfinite=lambda a: SimpleNamespace(all=lambda: bool(a.shape)),
                    ascontiguousarray=lambda a: a, testing=SimpleNamespace(assert_allclose=lambda *a, **k: None))}
        gate = guide_function('ci-asset-gate', 'ci_asset_gate', ns)
        args = ('/supplied-release.aimodel', Model(), SimpleNamespace(module=lambda: Model()), (Tensor(),))
        return gate, args, loader

    def test_composite_requirements_are_explicit(self):
        gate, args, loader = self.make_gate('')
        self.assertIs(inspect.signature(gate).parameters['required_composites'].default, inspect.Parameter.empty)
        with self.assertRaises(TypeError):
            gate(*args, runtime_atol=0, runtime_rtol=0)
        loader.assert_not_called()

    def test_empty_and_satisfied_requirements_own_output(self):
        for names in ((), ('rms_norm', 'rope', 'scaled_dot_product_attention')):
            ir = ' '.join(f'composite_declaration<"{n}"' for n in names)
            gate, args, loader = self.make_gate(ir)
            result = asyncio.run(gate(*args, runtime_atol=0, runtime_rtol=0, required_composites=names))
            self.assertEqual(result.shape, (1, 2))
            loader.assert_called_once_with(Path('/supplied-release.aimodel'))

    def test_missing_required_composite_fails(self):
        gate, args, _ = self.make_gate('composite_declaration<"rms_norm"')
        with self.assertRaisesRegex(AssertionError, 'missing composite: rope'):
            asyncio.run(gate(*args, runtime_atol=0, runtime_rtol=0, required_composites=('rms_norm', 'rope')))


if __name__ == '__main__':
    unittest.main()
