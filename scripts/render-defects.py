#!/usr/bin/env python3
"""Render registered current defect states into marked canonical guide blocks."""
import argparse
from collections import defaultdict
from pathlib import Path
import re
from refresh_defect_statuses import ROOT, load_registry, atomic_text
from mdslug import collect_headings


def render(root, write=False):
    by_file = defaultdict(list)
    for record in load_registry(root):
        for location in record['guideRefs']:
            if record not in by_file[location['file']]:
                by_file[location['file']].append(record)
    stale = []
    pattern = re.compile(r'<!-- current-defects:start -->.*?<!-- current-defects:end -->', re.S)
    scoped_pattern = re.compile(r'\n<!-- current-defect-refs:start -->.*?<!-- current-defect-refs:end -->\n', re.S)
    for path in sorted((root / 'guides').rglob('*.md')):
        relative = path.relative_to(root).as_posix()
        original = path.read_text()
        clean = scoped_pattern.sub('', original)
        records = by_file.get(relative, [])
        block = ''
        if records:
            rows = ['<!-- current-defects:start -->', '**Current tracked defects.** Closure, release availability, and demonstrated remediation are separate observations.', '', '| Reference | Recorded state/date | Verified release | Remediation | Disposition |', '|---|---|---|---|---|']
            for record in sorted(records, key=lambda item: item['id']):
                resolution = record['resolution']
                release = resolution['releaseAvailability']
                remediation = resolution['remediation']
                release_text = release['status'] + (f" ({release['version']})" if release['version'] else '')
                remediation_text = remediation['status'] + (f" ({remediation['version']})" if remediation['version'] else '')
                rows.append(f"| [{record['id']}]({record['url']}) <!-- defect-ref:{record['id']} --> | {record['claimedState']} ({record['asOf']}) | {release_text} | {remediation_text} | {resolution['disposition']} |")
            rows.append('<!-- current-defects:end -->')
            block = '\n'.join(rows)
        matches = pattern.findall(clean)
        if len(matches) > 1:
            raise ValueError(f'{relative}: duplicate current defect blocks')
        if matches:
            expected = pattern.sub(lambda match: block, clean)
        elif records:
            position = clean.find('\n## ')
            if position < 0:
                raise ValueError(f'{relative}: no section boundary for current defects')
            expected = clean[:position] + '\n\n' + block + '\n' + clean[position:]
        else:
            expected = clean
        by_anchor = defaultdict(set)
        for record in records:
            for location in record['guideRefs']:
                if location['file'] == relative:
                    by_anchor[location['anchor']].add(record['id'])
        lines = expected.splitlines(keepends=True)
        for heading in reversed(collect_headings(expected)):
            identifiers = by_anchor.get(heading.anchor)
            if identifiers:
                markers = ['\n<!-- current-defect-refs:start -->']
                markers.extend(f'<!-- defect-ref:{identifier} -->' for identifier in sorted(identifiers))
                markers.append('<!-- current-defect-refs:end -->\n')
                lines.insert(heading.line, '\n'.join(markers))
        expected = ''.join(lines)
        allowed = {record['id'] for record in records}
        locations = {record['id']: {location['anchor'] for location in record['guideRefs']
                     if location['file'] == relative} for record in records}
        scoped_text = pattern.sub('', expected)
        headings = iter(collect_headings(scoped_text))
        next_heading = next(headings, None)
        anchor = None
        for number, line in enumerate(scoped_text.splitlines(), 1):
            while next_heading and next_heading.line <= number:
                anchor = next_heading.anchor
                next_heading = next(headings, None)
            for identifier in re.findall(r'<!--\s*defect-ref:([^\s]+)\s*-->', line):
                if identifier not in allowed or anchor not in locations[identifier]:
                    raise ValueError(f'{relative}: unknown or misplaced defect ID {identifier}')
        if expected != original:
            stale.append(relative)
            if write:
                atomic_text(path, expected)
    if stale and not write:
        print('Stale defect blocks: ' + ', '.join(stale))
        return 1
    print(f'{"Updated" if write else "Verified"} current defect blocks.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write', action='store_true')
    parser.add_argument('--source-root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        raise SystemExit(render(args.source_root.resolve(), args.write))
    except ValueError as error:
        raise SystemExit(str(error))
