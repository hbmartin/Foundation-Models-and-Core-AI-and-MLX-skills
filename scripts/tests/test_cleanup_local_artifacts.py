import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('cleanup', ROOT / 'scripts/cleanup-local-artifacts.py')
cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('notes', 'guides', 'automations'): (self.root / name).mkdir()
        subprocess.run(['git', 'init', '-q', self.root], check=True)
        (self.root / '.gitignore').write_text('/.build/\n/probes/.build/\n/artifacts/\n')
        self.now = time.time()

    def old(self, path, days=60):
        for directory, dirs, files in os.walk(path, topdown=False):
            for name in dirs + files:
                p = Path(directory) / name
                if not p.is_symlink(): os.utime(p, (self.now-days*cleanup.DAY,)*2)
            os.utime(directory, (self.now-days*cleanup.DAY,)*2)

    def cache(self, name='old'):
        path = self.root / '.build' / name; path.mkdir(parents=True)
        (path / 'output').write_text('build'); self.old(path); return path

    def make_run(self, name, status='completed', days=60):
        path = self.root / 'artifacts/freshness/test' / name; path.mkdir(parents=True)
        (path / 'run.json').write_text(json.dumps({'status': status}))
        self.old(path, days); return path

    def test_old_caches_eligible_but_recent_descendants_protect(self):
        path = self.cache()
        self.assertEqual(cleanup.inventory(self.root)['candidates'][0]['path'], '.build/old')
        (path / 'fresh').write_text('active')
        self.assertEqual(cleanup.inventory(self.root)['candidates'], [])

    def test_newest_run_recent_runs_and_unresolved_failures_retained(self):
        old = self.make_run('old', days=90)
        self.make_run('new', days=60); self.make_run('recent', days=2)
        self.make_run('failed', 'failed'); self.make_run('active', 'running'); self.make_run('unknown', 'mystery')
        names = {r['path'] for r in cleanup.inventory(self.root)['candidates']}
        self.assertEqual(names, {str(old.relative_to(self.root)), 'artifacts/freshness/test/new'})

    def test_referenced_evidence_and_lock_run_ids_are_retained(self):
        old = self.make_run('old'); self.make_run('new', days=1)
        (self.root / 'notes/evidence.md').write_text('artifacts/freshness/test/old/run.json')
        self.assertEqual(cleanup.inventory(self.root)['candidates'], [])
        (self.root / 'notes/evidence.md').unlink()
        state = self.root / 'artifacts/freshness/state';state.mkdir()
        (state / 'weekly.lock').write_text(json.dumps({'runId': 'old'}))
        self.assertEqual(cleanup.inventory(self.root)['candidates'], [])

    def test_each_hosting_topology_retains_its_newest_completed_run(self):
        for mode, days in [('host', 60), ('device', 90), ('host-old', 100)]:
            path = self.make_run(mode, days=days)
            (path / 'run.json').write_text(json.dumps({'status': 'completed', 'hostingMode': mode.split('-')[0]}))
            self.old(path, days)
        names = {row['path'] for row in cleanup.inventory(self.root)['candidates']}
        self.assertEqual(names, {'artifacts/freshness/test/host-old'})

    def test_environment_asset_git_and_symlinks_are_protected(self):
        for name in ('pyvenv.cfg', 'toy.aimodel', 'model.safetensors', 'weights.gguf', '.git', 'active.lock'):
            p = self.cache(name.replace('.', '_')); (p / name).write_text('keep');self.old(p)
        outside = self.root / 'outside'; outside.mkdir(); (outside / 'keep').write_text('keep')
        p = self.cache('linked');(p/'escape').symlink_to(outside,target_is_directory=True);self.old(p)
        (self.root/'.build/alias').symlink_to(outside,target_is_directory=True)
        self.assertEqual(cleanup.inventory(self.root)['candidates'], [])
        self.assertTrue((outside/'keep').exists())

    def test_dry_run_and_apply_preserve_new_activity(self):
        p = self.cache(); report = cleanup.inventory(self.root)
        self.assertTrue(p.exists())
        (p/'fresh').write_text('active')
        self.assertEqual(cleanup.apply(report), [])
        self.old(p)
        report = cleanup.inventory(self.root)
        with mock.patch.object(cleanup.shutil.rmtree, 'avoids_symlink_attacks', True):
            self.assertEqual(cleanup.apply(report), ['.build/old'])
        self.assertFalse(p.exists())

    def test_apply_refuses_tracked_output_and_candidate_escape(self):
        p = self.cache()
        subprocess.run(['git','-C',self.root,'add','-f',p/'output'],check=True)
        self.assertEqual(cleanup.apply(cleanup.inventory(self.root)), [])
        report = cleanup.inventory(self.root)
        report['candidates'] = [{'path':'../outside','newestMtime':0}]
        self.assertEqual(cleanup.apply(report), [])

    def test_parent_symlink_replacement_cannot_redirect_deletion(self):
        p = self.cache(); report = cleanup.inventory(self.root)
        outside = self.root / 'outside'; (outside / 'old').mkdir(parents=True)
        (outside / 'old/keep').write_text('keep')
        original_open = cleanup.os.open
        replaced = False

        def replace_parent(path, flags, *args, **kwargs):
            nonlocal replaced
            if path == self.root.resolve() and not replaced:
                replaced = True
                (self.root / '.build').rename(self.root / 'saved-build')
                (self.root / '.build').symlink_to(outside, target_is_directory=True)
            return original_open(path, flags, *args, **kwargs)

        with mock.patch.object(cleanup.os, 'open', side_effect=replace_parent):
            self.assertEqual(cleanup.apply(report), [])
        self.assertTrue((outside / 'old/keep').exists())
        self.assertTrue((self.root / 'saved-build/old/output').exists())


if __name__ == '__main__': unittest.main()
