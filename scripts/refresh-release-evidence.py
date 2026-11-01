#!/usr/bin/env python3
"""Reconstruct dated release evidence from immutable interfaces and retained logs."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import shutil

from interface_drift import compare
from probe_evidence import summarize

ROOT = pathlib.Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reconstructed-at', required=True)
    parser.add_argument('--raw-runs', required=True, type=pathlib.Path)
    parser.add_argument('--header-root', required=True, type=pathlib.Path)
    args = parser.parse_args()
    release = ROOT / 'notes/evidence/release-27.2'
    validation = json.loads((release / 'validation.json').read_text())
    interfaces = ROOT / 'notes/sdk-interfaces'
    frameworks = []
    for after in sorted(interfaces.glob('*-27.2-macos.swiftinterface')):
        before = after.with_name(after.name.replace('-27.2-', '-27.0-'))
        if before.exists():
            changes = compare(before.read_text(), after.read_text())
            frameworks.append({'framework': after.name.split('-27.2-')[0],
                               'declarationsChanged': len(changes), 'changes': changes})
    write(release / 'interface-drift.json', {'schemaVersion': 2, 'reconstructedAt': args.reconstructed_at,
        'normalization': 'Scoped declarations; order-independent attributes; :: normalized to .; protocol requirements, accessors and inlined bodies retained. Raw captures unchanged.',
        'frameworks': frameworks})
    provenance = json.loads((release / 'mpp-header-provenance.json').read_text())
    for header in provenance['headers']:
        data = (args.header_root / header['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != header['sha256']:
            raise ValueError(f"header differs from retained 27.2 capture: {header['path']}")
        header['availability'] = [line.strip() for line in data.decode().splitlines()
            if line.lstrip().startswith(('#if', '#elif', '#define'))]
    provenance['reconstructedAt'] = args.reconstructed_at
    write(release / 'mpp-header-provenance.json', provenance)
    logs = release / 'logs';logs.mkdir(exist_ok=True)
    lanes = {}
    old_runtime = json.loads((ROOT / 'notes/evidence/runtime-current.json').read_text())
    runtime = {k: v for k, v in old_runtime.items() if k not in ('lanes', 'asOf')}
    runtime.update(asOf=validation['observedAt'], reconstructedAt=args.reconstructed_at, lanes=[])
    for name, filename in [('host', 'swift-test.log'), ('simulator', 'xcodebuild-test.log')]:
        run = args.raw_runs.resolve() / f'20261030-release-{name}'
        copied = logs / f'{name}.log'
        shutil.copyfile(run / 'Logs' / filename, copied)
        topology = {**validation['probes'][name], 'buildConfiguration': 'Debug'}
        lane = summarize(copied, run.relative_to(ROOT), topology)
        lane["sources"][0]["path"] = copied.relative_to(ROOT).as_posix()
        for key in ('tests', 'skipped', 'failures'):
            if lane['topology'][key] != validation['probes'][name][key]:
                raise ValueError(f'{name} {key} contradicts retained validation')
        lanes[name] = lane
        runtime['lanes'].append({'mode': name, **lane['topology'],
            'results': [row['raw'] for row in lane['results']],
            **{key: lane[key] for key in ('skipReasons', 'runDirectory', 'excludedTests', 'sources')}})
    write(release / 'probe-results.json', {'schemaVersion': 2, 'observedAt': validation['observedAt'], 'reconstructedAt': args.reconstructed_at, 'lanes': lanes})
    write(ROOT / 'notes/evidence/runtime-current.json', runtime)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
