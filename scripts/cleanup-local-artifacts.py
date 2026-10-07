#!/usr/bin/env python3
"""Dry-run cleanup of reproducible caches and explicitly completed local runs."""
from __future__ import annotations
import argparse
import datetime as dt
import errno
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DAY = 86400
SUCCESS = {'passed', 'success', 'succeeded', 'completed', 'no-change', 'ready-pr', 'reported'}
FAILURE = {'failed', 'blocked', 'interrupted', 'running', 'preparing', 'cleanup-pending', 'cleanup-failed'}


def tree_info(path):
    """Inspect without following links; retain environments, assets and Git checkouts."""
    newest, size, protected = path.lstat().st_mtime, 0, False
    for directory, dirs, files in os.walk(path, followlinks=False):
        current = Path(directory)
        for name in dirs + files:
            item = current / name
            if item.is_symlink():
                protected = True
                if name in dirs: dirs.remove(name)
                continue
            info = item.lstat(); newest = max(newest, info.st_mtime)
            if item.is_file(): size += info.st_size
            if name in {'.git', 'pyvenv.cfg', '.lock', 'lock', 'pytorch_model.bin', 'weights.bin', 'model.bin', 'tokenizer.model'} or name.endswith(('.aimodel', '.aimodelc', '.safetensors', '.gguf', '.pt', '.pth', '.onnx', '.mlmodel', '.mlpackage', '.lock')):
                protected = True
    return newest, size, protected


def run_status(path):
    """Unknown completion and failed/active records are retained conservatively."""
    statuses = []
    for name in ('run.json', 'validation.json', 'completion.json'):
        candidate = path / name
        if candidate.is_symlink(): return 'protected'
        if not candidate.is_file(): continue
        try:
            value = json.loads(candidate.read_text())
        except (OSError, ValueError): return 'unknown'
        if not isinstance(value, dict): return 'unknown'
        status = value.get('status') or value.get('outcome') or value.get('run_status')
        if status in FAILURE or value.get('error') or value.get('exitCode', 0) != 0:
            return 'failed-or-active'
        if isinstance(status, str): statuses.append(status)
    return 'completed' if statuses and all(status in SUCCESS for status in statuses) else 'unknown'


def references(root):
    pins = set()
    for base in ('notes', 'guides', 'automations'):
        for directory, dirs, files in os.walk(root / base, followlinks=False):
            dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
            for name in files:
                path = Path(directory) / name
                if path.is_symlink() or path.suffix not in {'.json', '.md', '.toml'}: continue
                text = path.read_text(errors='replace')
                for raw in re.findall(r'artifacts/(?:[A-Za-z0-9_.-]+/){2,}[A-Za-z0-9_.-]+', text):
                    target = root / raw.rstrip('.')
                    if target.exists(): pins.add(target)
    # Automation state is always retained; its run IDs pin active/pending work.
    state = root / 'artifacts/freshness/state'
    run_ids = set()
    if state.is_dir() and not state.is_symlink():
        for path in state.iterdir():
            if path.is_file() and not path.is_symlink():
                try:
                    raw = path.read_text()
                    run_ids.update(re.findall(r'"runId"\s*:\s*"([A-Za-z0-9_.-]+)"', raw))
                except OSError: pass
    return pins, run_ids


def run_topology(path):
    """Keep a baseline for each hosting mode/destination within a lane."""
    candidate = path / 'run.json'
    if candidate.is_symlink() or not candidate.is_file():
        return 'unspecified'
    value = json.loads(candidate.read_text())
    context = value.get('context', {})
    if not isinstance(context, dict):
        context = {}
    keys = ('topology', 'hostingMode', 'mode', 'destination', 'deviceIdentifier')
    return json.dumps({key: value.get(key, context.get(key)) for key in keys}, sort_keys=True)


def pinned(path, pins):
    return any(path == ref or path in ref.parents or ref in path.parents for ref in pins)


def inventory(root, now=None):
    root = root.resolve(); now = time.time() if now is None else now
    pins, run_ids = references(root)
    candidates, retained = [], []
    def consider(path, reason, age_days):
        if path.is_symlink() or not path.is_dir(): return
        relative = path.relative_to(root)
        if not any(relative == base or base in relative.parents for base in (Path('.build'), Path('probes/.build'), Path('artifacts/freshness'))):
            raise ValueError(f'outside designated ignored directories: {path}')
        if path.resolve() != path or pinned(path, pins):
            retained.append({'path': str(relative), 'reason': 'referenced or linked'}); return
        newest, size, protected = tree_info(path)
        if protected or now - newest < age_days * DAY:
            retained.append({'path': str(relative), 'reason': 'protected content or recent activity'}); return
        candidates.append({'path': str(relative), 'bytes': size, 'reason': reason, 'newestMtime': newest})
    for base in (root / '.build', root / 'probes/.build'):
        if base.is_symlink(): continue
        if base.is_dir():
            for child in sorted(base.iterdir()):
                consider(child, 'inactive reproducible cache older than seven days', 7)
    freshness = root / 'artifacts/freshness'
    if freshness.is_dir() and not freshness.is_symlink():
        for lane in sorted(freshness.iterdir()):
            if lane.name == 'state' or lane.is_symlink() or not lane.is_dir(): continue
            runs = [p for p in lane.iterdir() if p.is_dir() and not p.is_symlink()]
            completed = [p for p in runs if run_status(p) == 'completed']
            newest_runs = {}
            for path in completed:
                topology = run_topology(path)
                prior = newest_runs.get(topology)
                if prior is None or tree_info(path)[0] > tree_info(prior)[0]:
                    newest_runs[topology] = path
            for path in sorted(runs):
                status = run_status(path)
                if path.name in run_ids or status != 'completed':
                    retained.append({'path': str(path.relative_to(root)), 'reason': 'active, failed, or completion unknown'}); continue
                if path not in newest_runs.values():
                    consider(path, 'completed run older than thirty days', 30)
                else:
                    retained.append({'path': str(path.relative_to(root)), 'reason': 'newest completed run for lane/topology'})
                build = path / 'Build'
                if not pinned(path, pins) and build.is_dir():
                    consider(build, 'inactive reproducible cache older than seven days', 7)
    # A retained run can have an eligible build; a deleted run subsumes its build.
    candidates.sort(key=lambda row: len(Path(row['path']).parts))
    result = []
    for row in candidates:
        if not any(Path(parent['path']) in Path(row['path']).parents for parent in result): result.append(row)
    return {'schemaVersion': 1, 'root': str(root), 'generatedAt': dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(),
            'candidates': result, 'retained': retained, 'reclaimableBytes': sum(row['bytes'] for row in result)}


def apply(report):
    root = Path(report['root']).resolve()
    deleted = []
    for row in report['candidates']:
        # Re-inventory immediately before each removal; never trust a stale dry-run report.
        fresh = {item['path']: item for item in inventory(root)['candidates']}
        if row['path'] not in fresh or fresh[row['path']]['newestMtime'] != row['newestMtime']:
            continue
        path = root / row['path']
        if path.is_symlink() or path.resolve() != path or tree_info(path)[2]:
            continue
        relative = path.relative_to(root)
        ignored = subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', '--', str(relative)], capture_output=True)
        tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--', str(relative)], capture_output=True)
        if ignored.returncode != 0 or tracked.returncode != 0 or tracked.stdout:
            continue
        # fd-based rmtree rejects directory replacement with a symlink.
        if not shutil.rmtree.avoids_symlink_attacks:
            raise ValueError('this Python runtime lacks symlink-safe directory removal')
        # Open every ancestor with O_NOFOLLOW, then delete relative to the
        # pinned parent descriptor. rmtree's leaf protection alone would not
        # prevent a concurrently replaced parent from redirecting removal.
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(root, flags)
        try:
            expected = path.lstat()
            for part in relative.parts[:-1]:
                next_fd = os.open(part, flags, dir_fd=parent_fd)
                os.close(parent_fd)
                parent_fd = next_fd
            observed = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISDIR(observed.st_mode) or (observed.st_dev, observed.st_ino) != (expected.st_dev, expected.st_ino):
                continue
            shutil.rmtree(relative.name, dir_fd=parent_fd)
            deleted.append(row['path'])
        except OSError as error:
            if error.errno not in {errno.ENOENT, errno.ENOTDIR, errno.ELOOP}:
                raise
        finally:
            os.close(parent_fd)
    return deleted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    check = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    if check.returncode or Path(check.stdout.strip()).resolve() != root:
        parser.error('--root must identify a Git worktree root')
    report = inventory(root)
    report['mode'] = 'apply' if args.apply else 'dry-run'
    report['deleted'] = apply(report) if args.apply else []
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
