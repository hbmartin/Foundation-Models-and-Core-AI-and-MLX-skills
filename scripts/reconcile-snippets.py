#!/usr/bin/env python3
"""Merge a fresh partial compiler run with hash-identical historical target evidence."""
from __future__ import annotations
import argparse
import collections
import hashlib
import io
import importlib.util
import json
import pathlib
import os
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('snippet_reconciliation_verifier', ROOT / 'scripts/verify-snippets.py')
verifier = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = verifier
spec.loader.exec_module(verifier)


def reconcile(rows, prior, old_records, toolchains, checked_at):
    result, records = [], []
    seen = set()
    for fresh in rows:
        row = dict(fresh)
        if row['status'] in ('FAILED', 'MARKER-ERROR', 'PARSE-ERROR', 'XFAIL-ERR'):
            raise ValueError(f"fresh verification failed: {row['file']}:{row['line']}")
        key = (row['file'], row['snippet_id'])
        if not key[1] or key[1] == '-':
            raise ValueError(f"fresh verification has no snippet identity: {row['file']}:{row['line']}")
        if key in seen:
            raise ValueError(f"duplicate fresh snippet identity: {key}")
        seen.add(key)
        previous = prior.get(key)
        targets = {}
        for target, target_spec in verifier.TARGETS.items():
            column = target_spec.column
            verdict = row[column]
            if verdict == 'unavailable':
                record = old_records.get(key)
                if (previous is None or previous['content_hash'] != row['content_hash']
                        or record is None or record['content_hash'] != row['content_hash']):
                    continue
                historical = record['targets'].get(target)
                if historical is None or previous[column] not in ('pass', 'xfail-pass'):
                    continue
                row[column] = previous[column]
                targets[target] = {**historical, 'kind': 'historical-unchanged', 'freshCoverage': 'unavailable'}
            elif verdict != '-':
                targets[target] = {'kind': 'fresh', 'checkedAt': checked_at,
                                   'toolchain': toolchains[target], 'verdict': verdict}
        if row['status'] == 'TOOLCHAIN-UNAVAILABLE' and 'unavailable' not in [row[t.column] for t in verifier.TARGETS.values()]:
            markers = verifier.parse_markers(row['info'])
            row['status'] = ('MIGRATION-PROVEN' if markers.compile_targets and markers.xfail_targets else
                             'VERIFIED' if markers.compile_targets else 'XFAIL-PROVEN')
            row['first_error'], row['err_line'] = '-', '-'
        if targets:
            records.append({'file': row['file'], 'snippet_id': row['snippet_id'],
                            'content_hash': row['content_hash'], 'targets': targets})
        result.append(row)
    return result, records


def serialize_tsv(rows):
    stream = io.StringIO()
    verifier.write_tsv(rows, stream)
    return stream.getvalue().encode('utf-8')


def publish(payloads):
    """Stage every output before publication and roll back handled replace failures."""
    staged, backups, applied = {}, {}, []
    def stage(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name + '-', delete=False) as stream:
            temporary = pathlib.Path(stream.name)
            try:
                stream.write(data)
                os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        return temporary
    try:
        for path, data in payloads.items():
            staged[path] = stage(path, data)
            backups[path] = stage(path, path.read_bytes()) if path.exists() else None
        try:
            for path, temporary in staged.items():
                os.replace(temporary, path)
                applied.append(path)
        except BaseException:
            recovery_errors = []
            for path in reversed(applied):
                backup = backups[path]
                try:
                    if backup is None:
                        path.unlink(missing_ok=True)
                    else:
                        os.replace(backup, path)
                except OSError as error:
                    backups[path] = None  # Retain the recovery bytes on disk.
                    recovery_errors.append(f'recover {path} from {backup}: {error}')
            if recovery_errors:
                raise OSError('rollback failed; ' + '; '.join(recovery_errors))
            raise
    finally:
        for temporary in (*staged.values(), *backups.values()):
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fresh', required=True, type=pathlib.Path)
    parser.add_argument('--checked-at', required=True)
    parser.add_argument('--evidence', required=True, type=pathlib.Path)
    args = parser.parse_args()
    args.fresh = args.fresh.resolve()
    args.evidence = args.evidence.resolve()
    output = ROOT / 'notes/snippet-verification'
    old = json.loads((output / 'target-provenance.json').read_text())
    prior = verifier.read_prior_results(output / 'results.tsv')
    rows = verifier.read_results_rows(args.fresh / 'results.tsv')
    toolchains = json.loads((args.fresh / 'toolchains.json').read_text())
    old_records = {(r['file'], r['snippet_id']): r for r in old['records']}
    merged, records = reconcile(rows, prior, old_records, toolchains, args.checked_at)
    fences, errors = verifier.extract_fences(str(ROOT / "guides"))
    if errors:
        raise ValueError("current guides contain malformed fences")
    current = {(f.rel_path, verifier.fence_identity(f)[0]): f for f in fences}
    if len(current) != len(merged):
        raise ValueError("fresh run does not cover the current snippet inventory")
    for row in merged:
        fence = current.get((row["file"], row["snippet_id"]))
        if fence is None or verifier.fence_identity(fence)[1] != row["content_hash"]:
            raise ValueError(f"snippet changed since fresh verification: {row['file']}:{row['line']}")
        row.update(line=str(fence.open_line), anchor=fence.anchor, info=fence.info or "-")
    payloads = {output / 'results.tsv': serialize_tsv(merged)}
    digest = hashlib.sha256()
    for path in sorted((ROOT / 'guides').glob('part-*/**/*.md')):
        digest.update(path.relative_to(ROOT).as_posix().encode());digest.update(b'\0');digest.update(path.read_bytes())
    provenance = {'schemaVersion': old['schemaVersion'], 'checkedAt': args.checked_at,
                  'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  'reconciledGuideTreeSha256': digest.hexdigest(), 'workingTreeGuides': True,
                  'freshIncomplete': any('unavailable' in t for t in toolchains.values()),
                  'unavailableTargets': [name for name, tc in toolchains.items() if 'unavailable' in tc],
                  'records': records}
    payloads[output / 'target-provenance.json'] = (json.dumps(provenance, indent=2) + '\n').encode('utf-8')
    historical_count = sum(t['kind'] == 'historical-unchanged' for r in records for t in r['targets'].values())
    counts = dict(sorted(collections.Counter(r['status'] for r in merged).items()))
    summary = ' · '.join(f'{key} {value}' for key, value in counts.items())
    preamble = (f'# Reconciled snippet inventory — {args.checked_at}\n\n'
        f'The current ledger contains **{len(merged):,} fences**: {summary}.\n\n'
        f'The available SDK-27 targets were freshly checked. {historical_count} hash-identical SDK-26 target verdicts\n'
        'retain their historical toolchains and dates; SDK 26 is unavailable. The report below is the\n'
        'fresh **partial** run, whose unavailable counts differ from the reconciled ledger.\n'
        'Base revision and the reconciled guide-tree digest are recorded in `target-provenance.json`;\n'
        'individual content hashes bind compiler verdicts to the exact snippet bodies.\n'
        'The original October 30 partial evidence remains dated and unchanged in `notes/evidence/release-27.2/`.\n\n'
        '## Latest available-target compiler run\n\n')
    payloads[output / 'report.md'] = (preamble + (args.fresh / 'report.md').read_text()).encode('utf-8')
    state_path = ROOT / 'notes/current-state.json';state = json.loads(state_path.read_text())
    state['asOf'] = args.checked_at
    state['verification'].update(lastAvailableRun=args.checked_at, statusCounts=counts,
        freshPartialResult=(args.evidence / 'results.tsv').relative_to(ROOT).as_posix(),
        blocker=f'SDK-26 targets unavailable. Available SDK-27 targets checked {args.checked_at}; {historical_count} unchanged SDK-26 target verdicts retain historical provenance.')
    payloads[state_path] = (json.dumps(state, indent=2, sort_keys=True) + '\n').encode('utf-8')
    for filename in ('results.tsv', 'report.md', 'toolchains.json'):
        evidence_path = args.evidence / filename
        if evidence_path in payloads:
            raise ValueError('evidence directory overlaps the canonical ledger')
        payloads[evidence_path] = (args.fresh / filename).read_bytes()
    publish(payloads)
    print(json.dumps({'fences': len(merged), 'statusCounts': counts, 'historicalTargets': historical_count}))


if __name__ == '__main__':
    raise SystemExit(main())
