"""Portable security controls: no Core AI installation or guide execution needed."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zlib
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('native_verifier', ROOT / 'scripts/verify_coreai_examples.py')
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


class NativeRevisionTrustTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runner, self.source = self.root / 'runner', self.root / 'source'
        for folder in (self.runner, self.source):
            folder.mkdir()
            git(folder, 'init', '-q')
            git(folder, 'config', 'user.email', 'test@example.invalid')
            git(folder, 'config', 'user.name', 'Test')
            (folder / '.gitignore').write_text('__pycache__/\n*.pyc\n')
            (folder / 'scripts').mkdir()
            for name in ('verify_coreai_examples.py', 'coreai_examples.py', 'mdlinks.py'):
                shutil.copy2(ROOT / 'scripts' / name, folder / 'scripts' / name)
            guide = folder / 'guides/part-08-fixture/example.md'
            guide.parent.mkdir(parents=True)
            guide.write_text('<!-- coreai-example: {"id":"state-protocol"} -->\n```python\nvalue = 42\n```\n')
            git(folder, 'add', '.')
            git(folder, 'commit', '-qm', 'reviewed fixture')
        self.revision = git(self.source, 'rev-parse', 'HEAD')

    def snapshots(self, **kwargs):
        return VERIFIER.approved_snapshots(self.runner, self.source, self.revision,
            isolated=kwargs.get('isolated', True), optimize=kwargs.get('optimize', 0))

    def test_clean_control_and_immutable_read(self):
        runner_sha, runner, source = self.snapshots()
        reader = VERIFIER.load_trusted_reader(runner)
        example = VERIFIER.snapshot_examples(reader, source)['state-protocol']
        self.assertEqual(example.line, 3)
        self.assertEqual(example.code, 'value = 42\n')
        (self.source / example.path).write_text('changed after validation')
        self.assertEqual(VERIFIER.snapshot_examples(reader, source)['state-protocol'].code, example.code)
        self.assertEqual(runner_sha, git(self.runner, 'rev-parse', 'HEAD'))

    def test_revision_and_interpreter_fail_closed(self):
        for revision in ('HEAD', self.revision[:8], 'A' * 40, 'f' * 40):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                VERIFIER.approved_snapshots(self.runner, self.source, revision, isolated=True, optimize=0)
        for kwargs in ({'isolated': False}, {'optimize': 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.snapshots(**kwargs)
        with self.assertRaisesRegex(ValueError, 'separate checkouts'):
            VERIFIER.approved_snapshots(self.runner, self.runner, self.revision, isolated=True, optimize=0)

    def test_cli_rejects_optimized_and_nonisolated_before_imports(self):
        script = self.runner / 'scripts/verify_coreai_examples.py'
        args = ['--source-repo', str(self.source), '--reviewed-revision', self.revision,
                '--out', str(self.root / 'result.json')]
        for flags, expected in (([], 'python -I'), (['-I', '-O'], 'optimized Python')):
            r = subprocess.run([sys.executable, *flags, str(script), *args], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(expected, r.stderr)
        self.assertFalse((self.root / 'result.json').exists())

    def test_dirty_bytes_index_modes_and_hidden_index_flags(self):
        target = self.source / 'guides/part-08-fixture/example.md'
        original = target.read_bytes()
        for flag in ('--assume-unchanged', '--skip-worktree'):
            git(self.source, 'update-index', flag, str(target.relative_to(self.source)))
            target.write_text('not reviewed')
            with self.assertRaisesRegex(ValueError, 'tracked edit'):
                self.snapshots()
            target.write_bytes(original)
            git(self.source, 'update-index', '--no-' + flag[2:], str(target.relative_to(self.source)))
        target.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'tracked edit'):
            self.snapshots()
        target.chmod(0o644)
        target.unlink()
        with self.assertRaisesRegex(ValueError, 'missing tracked'):
            self.snapshots()
        target.write_bytes(original)
        (self.source / 'extra.py').write_text('raise RuntimeError("unreviewed")')
        with self.assertRaisesRegex(ValueError, 'untracked'):
            self.snapshots()
        git(self.source, 'add', 'extra.py')
        with self.assertRaisesRegex(ValueError, 'staged files'):
            self.snapshots()

    def test_dirty_runner_and_symlink_substitution_rejected(self):
        helper = self.runner / 'scripts/coreai_examples.py'
        helper.write_text('raise RuntimeError("dirty runner")')
        with self.assertRaisesRegex(ValueError, 'tracked edit'):
            self.snapshots()
        target = self.source / 'guides/part-08-fixture/example.md'
        payload = target.read_bytes()
        target.unlink()
        alternate = self.root / 'alternate.md'
        alternate.write_bytes(payload)
        target.symlink_to(alternate)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            VERIFIER.clean_snapshot(self.source, self.revision)

    def test_candidate_modules_and_ignored_bytecode_never_imported(self):
        for name in ('scripts/coreai_examples.py', 'scripts/mdlinks.py', 'torch.py', 'sitecustomize.py'):
            (self.source / name).write_text('raise RuntimeError("candidate module executed")\n')
        git(self.source, 'add', '.')
        git(self.source, 'commit', '-qm', 'reviewed text with untrusted candidate modules')
        self.revision = git(self.source, 'rev-parse', 'HEAD')
        bytecode = self.runner / 'scripts/__pycache__'
        bytecode.mkdir()
        (bytecode / 'coreai_examples.cpython-312.pyc').write_bytes(b'poison')
        _, runner, source = self.snapshots()
        reader = VERIFIER.load_trusted_reader(runner)
        self.assertEqual(VERIFIER.snapshot_examples(reader, source)['state-protocol'].code, 'value = 42\n')

    def test_git_hooks_filters_and_inherited_git_environment_ignored(self):
        sentinel = self.root / 'configured-command-ran'
        callback = self.source / '.git/callback'
        callback.write_text('#!/bin/sh\ntouch "' + str(sentinel) + '"\n')
        callback.chmod(0o755)
        git(self.source, 'config', 'core.fsmonitor', str(callback))
        git(self.source, 'config', 'filter.poison.clean', str(callback))
        git(self.source, 'config', 'filter.poison.process', str(callback))
        (self.source / '.git/info/attributes').write_text('* filter=poison\n')
        with mock.patch.dict(os.environ, {'GIT_DIR': '/missing', 'GIT_WORK_TREE': '/missing',
            'GIT_INDEX_FILE': '/missing', 'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'core.fsmonitor',
            'GIT_CONFIG_VALUE_0': str(callback)}):
            self.snapshots()
        self.assertFalse(sentinel.exists())

    def test_replacement_refs_do_not_substitute_reviewed_tree(self):
        original = self.revision
        target = self.source / 'guides/part-08-fixture/example.md'
        target.write_text('attacker replacement tree')
        git(self.source, 'add', '.')
        git(self.source, 'commit', '-qm', 'replacement')
        replacement = git(self.source, 'rev-parse', 'HEAD')
        git(self.source, 'checkout', '-q', original)
        git(self.source, 'replace', original, replacement)
        _, runner, source = self.snapshots()
        reader = VERIFIER.load_trusted_reader(runner)
        self.assertIn('value = 42', VERIFIER.snapshot_examples(reader, source)['state-protocol'].code)

    def test_substituted_nested_tree_and_commit_objects_rejected(self):
        oid = git(self.source, 'rev-parse', self.revision + ':guides/part-08-fixture')
        database = self.source / '.git/objects'
        nested = database / oid[:2] / oid[2:]
        original = nested.read_bytes()
        nested.chmod(0o600)
        raw = zlib.decompress(original)
        # Valid, different tree bytes deliberately stored under the reviewed OID.
        nested.write_bytes(zlib.compress(raw.replace(b'example.md', b'altered.md')))
        with self.assertRaisesRegex(ValueError, 'tree digest mismatch'):
            self.snapshots()
        nested.write_bytes(original)
        commit = database / self.revision[:2] / self.revision[2:]
        raw = zlib.decompress(commit.read_bytes())
        commit.chmod(0o600)
        commit.write_bytes(zlib.compress(raw.replace(b'reviewed fixture', b'altered fixture!')))
        with self.assertRaisesRegex(ValueError, 'commit digest mismatch'):
            self.snapshots()

    def test_snapshot_parser_rejects_optimizer_and_metadata_errors(self):
        _, runner, source = self.snapshots()
        reader = VERIFIER.load_trusted_reader(runner)
        key = 'guides/part-08-fixture/example.md'
        for text, error in (('```python\nx.to_coreai().optimize()\n```', 'removed .optimize'),
                            ('```python\nx = (\n```', 'tokenization'),
                            ('<!-- coreai-example: nope -->\n```python\nx=1\n```', 'Expecting value')):
            source[key] = text.encode()
            with self.subTest(text=text), self.assertRaises(ValueError):
                VERIFIER.snapshot_examples(reader, source)
        duplicate = b'<!-- coreai-example: {"id":"same"} -->\n```python\nx=1\n```'
        source[key] = duplicate
        source['guides/part-08-fixture/other.md'] = duplicate
        with self.assertRaisesRegex(ValueError, 'duplicate corpus'):
            VERIFIER.snapshot_examples(reader, source)
