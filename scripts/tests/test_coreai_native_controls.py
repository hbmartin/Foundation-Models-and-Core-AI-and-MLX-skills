"""Portable checks for native recording and selected guide contracts; no SDK imports."""
import ast
import asyncio
from contextlib import nullcontext
import importlib.metadata
import inspect
import json
import os
import stat
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
    def run_setup(self, *, compression=False, missing=None, command_failure=None, native_error=None, fixture_error=None):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'record.json'
            argv = ['verifier', '--source-repo', '/unused', '--reviewed-revision', 'a' * 40,
                    '--out', str(output)] + (['--compression'] if compression else [])
            names = ['state-protocol', 'shipped-asset-gate', 'ci-asset-gate',
                     'compression-native-fixtures', 'composite-quantization']
            blobs = dict.fromkeys(('scripts/verify_coreai_examples.py',
                                  'scripts/coreai_examples.py', 'scripts/mdlinks.py'), b'fixture')
            queried = []
            examples = dict.fromkeys(names)
            native_modules = {}
            if fixture_error is not None:
                code = ("import asyncio\n"
                        "def convert_state_model(path): return None, None\n"
                        f"async def verify_state_asset(*args, **kwargs): raise asyncio.{type(fixture_error).__name__}('fixture cancelled')\n")
                examples['state-protocol'] = SimpleNamespace(code=code, line=1, path=Path('state-fixture.py'))
                native_modules = {'numpy': SimpleNamespace(int64=int, float32=float, bool_=bool,
                    array=lambda x: x, int32=int), 'torch': SimpleNamespace(),
                    'coreai_torch': SimpleNamespace(TorchConverter=None, get_decomp_table=None)}

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
                if name == 'numpy' and fixture_error is None:
                    raise native_error or RuntimeError('portable test stops before native execution')
                return real_import(name, *args, **kwargs)

            with mock.patch.object(sys, 'argv', argv), \
                    mock.patch.object(verifier, 'approved_snapshots', return_value=('b' * 40, blobs, {})), \
                    mock.patch.object(verifier, 'load_trusted_reader'), \
                    mock.patch.object(verifier, 'snapshot_examples', return_value=examples), \
                    mock.patch.object(verifier.platform, 'platform', return_value='fixture-os'), \
                    mock.patch.object(verifier.importlib.metadata, 'version', side_effect=version), \
                    mock.patch.object(verifier.subprocess, 'check_output', side_effect=command), \
                    mock.patch.dict(sys.modules, native_modules), \
                    mock.patch('builtins.__import__', side_effect=stop_native_import):
                escaping = fixture_error or native_error
                propagates = isinstance(escaping, BaseException) and not isinstance(
                    escaping, (Exception, KeyboardInterrupt, SystemExit))
                if propagates:
                    with self.assertRaises(type(escaping)):
                        verifier.main()
                else:
                    status = verifier.main()
                    self.assertEqual(status, 130 if isinstance(native_error, KeyboardInterrupt) else 1)
            record = json.loads(output.read_text())
            self.assertEqual(record['source_revision'], 'a' * 40)
            if propagates or isinstance(native_error, KeyboardInterrupt):
                self.assertEqual(record['run_status'], 'interrupted')
            else:
                self.assertEqual(record['fixtures'][-1]['outcome'], 'FAIL')
                self.assertEqual(record['run_status'], 'failed')
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

    def test_setup_exit_zero_is_a_recorded_failure(self):
        record, _ = self.run_setup(native_error=SystemExit(0))
        self.assertIn('SystemExit: 0', record['fixtures'][-1]['details'])

    def test_setup_keyboard_interrupt_is_recorded(self):
        self.run_setup(native_error=KeyboardInterrupt())

    def test_setup_cancellation_and_other_base_exceptions_finalize_before_propagating(self):
        for error in (asyncio.CancelledError('setup cancelled'), GeneratorExit('setup stopped')):
            with self.subTest(error=type(error).__name__):
                record, _ = self.run_setup(native_error=error)
                self.assertEqual(record['fixtures'], [])

    def test_fixture_cancellation_retains_completed_results_and_skips_remaining_fixtures(self):
        record, _ = self.run_setup(fixture_error=asyncio.CancelledError())
        self.assertEqual([f['name'] for f in record['fixtures']], ['NumPy scalar/array fixture details'])
        self.assertEqual(record['fixtures'][0]['outcome'], 'PASS')
        self.assertEqual(set(record['examples']), {'state-protocol'})

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


class CheckpointTests(unittest.TestCase):
    def test_bad_details_and_exit_preserve_results_and_continue(self):
        def exit_zero():
            raise SystemExit(0)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'results.json'
            record = {'fixtures': []}
            recorder = verifier.RunRecorder(output, record)
            self.assertEqual(json.loads(output.read_text())['run_status'], 'running')
            fixtures = [('earlier', lambda: {'value': 1}), ('unsupported', lambda: object()),
                        ('nonfinite', lambda: float('nan')), ('exit', exit_zero), ('later', lambda: 2)]
            for i, (name, fn) in enumerate(fixtures, 1):
                recorder.check(name, fn)
                self.assertEqual(len(json.loads(output.read_text())['fixtures']), i)
            self.assertEqual(recorder.finish(), 1)
            saved = json.loads(output.read_text())
            self.assertEqual(saved['run_status'], 'failed')
            self.assertEqual([x['outcome'] for x in saved['fixtures']], ['PASS', 'FAIL', 'FAIL', 'FAIL', 'PASS'])
            self.assertIn('serialization failed', saved['fixtures'][1]['details'])
            self.assertIn('SystemExit: 0', saved['fixtures'][3]['details'])

    def test_publication_preserves_existing_mode_and_new_file_umask(self):
        with tempfile.TemporaryDirectory() as folder:
            existing = Path(folder) / 'existing.json'
            existing.write_text('{}')
            existing.chmod(0o640)
            verifier.publish_record(existing, {'fixtures': []})
            self.assertEqual(stat.S_IMODE(existing.stat().st_mode), 0o640)
            for mask in (0o022, 0o077):
                previous_umask = os.umask(mask)
                try:
                    output = Path(folder) / f'new-{mask}.json'
                    verifier.publish_record(output, {'fixtures': []})
                finally:
                    os.umask(previous_umask)
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o666 & ~mask)
                self.assertEqual(json.loads(output.read_text()), {'fixtures': []})
            self.assertFalse(any(p.name.startswith('.') for p in Path(folder).iterdir()))

    def test_supported_numpy_values_paths_and_tuples(self):
        # Portable facsimiles exercise the optional NumPy adapter. Both native
        # profiles additionally return real NumPy scalars/arrays through it.
        class Scalar:
            def __init__(self, value): self.value = value
            def item(self): return self.value
        class Array:
            def tolist(self): return [[1, 2], [3, 4]]
        numpy = SimpleNamespace(generic=Scalar, ndarray=Array)
        with mock.patch.dict(sys.modules, {'numpy': numpy}):
            result = verifier.fixture_result('supported', lambda: {
                'scalar': Scalar(3), 'array': Array(), 'tuple': (Scalar(True), Path('asset.aimodel'))})
        self.assertEqual(result['outcome'], 'PASS')
        self.assertEqual(json.loads(json.dumps(result))['details'], {
            'scalar': 3, 'array': [[1, 2], [3, 4]], 'tuple': [True, 'asset.aimodel']})

    def test_serialization_cannot_satisfy_a_negative_control(self):
        result = verifier.fixture_result('bad', lambda: object(), (TypeError, 'unsupported fixture detail'))
        self.assertEqual(result['outcome'], 'FAIL')
        self.assertNotEqual(result['details'], 'unsupported fixture detail')
        for value in (float('inf'), float('-inf'), {1: 'key'}, complex(1, 2)):
            self.assertEqual(verifier.fixture_result('bad', lambda: value)['outcome'], 'FAIL')

    def test_interrupt_preserves_completed_fixture(self):
        def interrupt(): raise KeyboardInterrupt()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'results.json'
            recorder = verifier.RunRecorder(output, {'fixtures': []})
            recorder.check('earlier', lambda: 1)
            with self.assertRaises(KeyboardInterrupt):
                recorder.check('interrupted', interrupt)
            self.assertEqual(recorder.finish(interrupted=True), 130)
            saved = json.loads(output.read_text())
            self.assertEqual(saved['run_status'], 'interrupted')
            self.assertEqual([x['name'] for x in saved['fixtures']], ['earlier'])

    def test_failed_publication_preserves_checkpoint_and_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'results.json'
            recorder = verifier.RunRecorder(output, {'fixtures': []})
            recorder.check('earlier', lambda: 1)
            previous = output.read_bytes()
            later = mock.Mock()
            with mock.patch.object(verifier.os, 'replace', side_effect=OSError('disk failure')):
                with self.assertRaisesRegex(verifier.RecordWriteError, 'disk failure'):
                    recorder.check('next', lambda: 2)
                    later()
                with self.assertRaises(verifier.RecordWriteError):
                    recorder.finish()
            later.assert_not_called()
            self.assertEqual(output.read_bytes(), previous)
            self.assertEqual(list(Path(folder).iterdir()), [output])


class StandaloneCompositeTests(unittest.TestCase):
    def test_inert_entrypoint_cannot_pass_or_reuse_an_old_asset(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / 'composite-demo/composite-quantized.aimodel').mkdir(parents=True)
            compare = mock.Mock()
            load = mock.Mock(return_value={})
            previous = Path.cwd()
            with self.assertRaisesRegex(AssertionError, 'did not create an asset'):
                verifier.standalone_composite_check(work, load, {'compare_composite_asset': compare})
            load.assert_called_once_with('composite-quantization', module_name='__main__')
            compare.assert_not_called()
            self.assertEqual(Path.cwd(), previous)

    def test_created_asset_is_independently_compared(self):
        with tempfile.TemporaryDirectory() as folder:
            def load(*args, **kwargs):
                path = Path('composite-demo/composite-quantized.aimodel')
                path.mkdir(parents=True)
                (path / 'model.bin').write_bytes(b'new asset')
            def compare(path):
                self.assertEqual((path / 'model.bin').read_bytes(), b'new asset')
                return {'conversion_max_abs': 0.001, 'compression_quality_max_abs': 0.02}
            result = verifier.standalone_composite_check(Path(folder), load, {'compare_composite_asset': compare})
            self.assertTrue(result['asset_created'])
            self.assertEqual(result['conversion_max_abs'], 0.001)
            with self.assertRaisesRegex(AssertionError, 'wrong asset'):
                verifier.standalone_composite_check(Path(folder), load, {
                    'compare_composite_asset': lambda path: (_ for _ in ()).throw(AssertionError('wrong asset'))})


class CompressionRuntimeContractTests(unittest.TestCase):
    def runtime(self, example_id, name, *, keys=('y',), finite_input=True, finite_output=True,
                input_names=('x',), output_names=('y',), state_names=()):
        class Array:
            def __init__(self, finite=True): self.finite, self.valid = finite, True
            def copy(self):
                if not self.valid: raise RuntimeError('expired borrowed array')
                return Array(self.finite)
        borrowed = Array(finite_output)
        calls = []
        class Function:
            desc = SimpleNamespace(input_names=input_names, output_names=output_names, state_names=state_names)
            async def __call__(self, **kwargs):
                calls.append(kwargs)
                return {key: SimpleNamespace(numpy=lambda: borrowed) for key in keys}
        class Executable:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): borrowed.valid = False
            def load_function(self, name): return Function()
        asset = SimpleNamespace(executable=Executable)
        def finite(array):
            if not array.valid: raise RuntimeError('expired borrowed array')
            return SimpleNamespace(all=lambda: array.finite)
        ns = {'Path': Path, 'AIModelAsset': SimpleNamespace(load=lambda path: asset),
              'NDArray': lambda value: value, 'np': SimpleNamespace(isfinite=finite)}
        fn = guide_function(example_id, name, ns)
        sample = SimpleNamespace(numpy=lambda: Array(finite_input))
        return fn, sample, calls

    def test_both_runtime_helpers_copy_and_check_contracts(self):
        for example_id, name in (('composite-quantization', 'composite_runtime'),
                                 ('compression-native-fixtures', 'fixture_runtime')):
            with self.subTest(name=name):
                fn, sample, calls = self.runtime(example_id, name)
                result = asyncio.run(fn('/asset', sample))
                self.assertTrue(result.valid)
                self.assertEqual(len(calls), 1)
            for options in ({'keys': ('y', 'extra')}, {'keys': ()}, {'finite_input': False},
                            {'finite_output': False}, {'input_names': ('wrong',)},
                            {'output_names': ('wrong',)}, {'state_names': ('unexpected',)}):
                with self.subTest(name=name, options=options):
                    fn, sample, _ = self.runtime(example_id, name, **options)
                    with self.assertRaises(AssertionError):
                        asyncio.run(fn('/asset', sample))


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
