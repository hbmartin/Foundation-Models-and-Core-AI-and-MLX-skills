from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from scripts import refresh_defect_statuses as reporter
from scripts.mdslug import collect_headings

ROOT = Path(__file__).resolve().parents[2]


class DefectRegistryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / 'notes').mkdir()
        (self.root / 'guides').mkdir()
        (self.root / 'guides/test.md').write_text('# Test\n\n## Current\n\n<!-- defect-ref:owner.repo:issue:19 -->\nAn unrelated #19 was open.\n')
        self.record = {'id': 'owner.repo:issue:19', 'url': 'https://github.com/owner/repo/issues/19',
                       'kind': 'issue', 'affectedVersions': 'Version boundary not established.',
                       'guideRefs': [{'file': 'guides/test.md', 'anchor': 'current'}],
                       'claimedState': 'OPEN', 'asOf': '2026-10-07',
                       'resolution': {'disposition': 'unknown', 'evidenceUrls': ['https://github.com/owner/repo/issues/19'],
                                      'evidenceDate': '2026-10-07', 'rationale': 'Closure is not a verified fix.', 'confidence': 1.0,
                                      'releaseAvailability': {'status': 'unknown', 'version': None, 'evidenceUrls': []},
                                      'remediation': {'status': 'unverified', 'version': None, 'evidenceUrls': []}}}
        self.write([self.record])

    def write(self, records):
        (self.root / 'notes/defects.json').write_text(json.dumps({'schemaVersion': 1, 'defects': records}))

    def test_extraction_uses_only_registry_claims(self):
        (self.root / 'guides/test.md').write_text('# Test\n## Current\n<!-- defect-ref:owner.repo:issue:19 -->\n#999 is CLOSED, not open.\n')
        rows = reporter.extract(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['number'], rows[0]['claimedState'], rows[0]['line']), (19, 'OPEN', 2))
        self.assertEqual(rows[0]['registryId'], self.record['id'])

    def test_kind_namespaces_remain_separate(self):
        discussion = copy.deepcopy(self.record)
        discussion.update(id='owner.repo:discussion:19', kind='discussion', url='https://github.com/owner/repo/discussions/19')
        pull = copy.deepcopy(self.record)
        pull.update(id='owner.repo:pull:19', kind='pull', url='https://github.com/owner/repo/pull/19')
        self.write([self.record, discussion, pull])
        guide = self.root / 'guides/test.md'
        guide.write_text(guide.read_text() + '<!-- defect-ref:owner.repo:discussion:19 -->\n<!-- defect-ref:owner.repo:pull:19 -->\n')
        refs = reporter.group_references(reporter.extract(self.root), False, 0)
        self.assertEqual(len(refs), 3)
        self.assertEqual(len({r['registryId'] for r in refs}), 3)

    def test_invalid_registry_and_missing_or_unsafe_targets_fail(self):
        variants = []
        for changes in ({'kind': 'discussion'}, {'claimedState': 'MERGED'}, {'asOf': '2026-99-99'},
                        {'affectedVersions': ''}, {'guideRefs': [{'file': 'guides/missing.md', 'anchor': 'current'}]},
                        {'guideRefs': [{'file': '../escape.md', 'anchor': 'current'}]},
                        {'guideRefs': [{'file': 'guides/test.md', 'anchor': 'missing'}]}):
            value = copy.deepcopy(self.record); value.update(changes); variants.append([value])
        variants.append([self.record, self.record])
        for value in variants:
            self.write(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                reporter.load_registry(self.root)

    def test_heading_namespace_ignores_fences_and_handles_duplicates(self):
        text = '# Test\n```md\n## Ignored\n```\n## Current\n## Current\n'
        headings = collect_headings(text)
        self.assertEqual([(h.line, h.anchor) for h in headings], [(1, 'test'), (5, 'current'), (6, 'current-1')])

    def test_state_transition_does_not_establish_fix(self):
        live = {'kind': 'issue', 'state': 'CLOSED', 'url': self.record['url'], 'title': 'Closed', 'closedAt': '2026-10-07', 'mergedAt': None}
        with mock.patch.object(reporter, 'lookup', return_value=live):
            refs = reporter.group_references(reporter.extract(self.root), True, 0)
        self.assertEqual(refs[0]['verdict'], 'STATE-CHANGED')
        self.assertEqual(refs[0]['transitionKind'], 'OPEN_TO_CLOSED')
        self.assertEqual(refs[0]['resolutionDisposition'], 'unknown')
        self.assertFalse(refs[0]['automaticFixEligible'])

    def test_release_and_remediation_require_separate_evidence(self):
        value = copy.deepcopy(self.record)
        value['resolution']['disposition'] = 'fixed'
        self.write([value])
        with self.assertRaisesRegex(ValueError, 'demonstrated remediation'):
            reporter.load_registry(self.root)
        value['resolution']['remediation'] = {'status': 'demonstrated', 'version': '1.2', 'evidenceUrls': [self.record['url']]}
        self.write([value])
        loaded = reporter.load_registry(self.root)[0]
        self.assertEqual(loaded['resolution']['releaseAvailability']['status'], 'unknown')

    def test_failed_lookup_is_visible_in_changed_only_json_and_markdown(self):
        args = reporter.parse_arguments(['--source-root', str(self.root), '--changed-only', '--format', 'json'])
        with mock.patch.object(reporter, 'lookup', return_value={'error': 'offline'}):
            payload = json.loads(reporter.render(args))
            args.format = 'markdown'; markdown = reporter.render(args)
        self.assertEqual(payload['references'], [])
        self.assertEqual(payload['summary']['verdicts']['UNREACHABLE'], 1)
        self.assertEqual(payload['unreachableReferences'][0]['live']['error'], 'offline')
        self.assertIn('Failed GitHub lookups', markdown)
        self.assertIn('offline', markdown)

    def test_lookup_uses_explicit_endpoint(self):
        data = {'state': 'closed', 'html_url': 'https://github.com/owner/repo/pull/19', 'title': 'Fix', 'merged_at': '2026-10-07'}
        with mock.patch.object(reporter, 'gh_json', return_value=(data, None)) as query:
            result = reporter.lookup('owner/repo', 19, 'pull')
        query.assert_called_once_with('api', 'repos/owner/repo/pulls/19')
        self.assertEqual(result['state'], 'MERGED')
        with mock.patch.object(reporter, 'gh_json', return_value=(None, 'offline')) as query:
            self.assertEqual(reporter.lookup('owner/repo', 19, 'issue'), {'error': 'offline'})
        query.assert_called_once_with('api', 'repos/owner/repo/issues/19')
        collision = dict(data, pull_request={'url': self.record['url']})
        with mock.patch.object(reporter, 'gh_json', return_value=(collision, None)):
            result = reporter.lookup('owner/repo', 19, 'issue')
        self.assertIn('registry declares an issue', result['error'])

    def test_cli_atomic_json_and_legacy_tsv_columns(self):
        output = self.root / 'report.json'; output.write_text('old'); output.chmod(0o640)
        result = subprocess.run([sys.executable, ROOT / 'scripts/refresh_defect_statuses.py', '--source-root', self.root,
                                 '--extract-only', '--format', 'json', '--output', output], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(output.read_text())['schemaVersion'], 2)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o640)
        self.assertEqual(reporter.sighting_tsv(reporter.extract(self.root)).splitlines()[0],
                         'file\tline\trepo\tnumber\tform\tclaimed_state\tclaim_date\tcontext')

    def test_wrapper_resolves_output_from_repository_root(self):
        output = self.root / 'wrapper.json'
        result = subprocess.run([ROOT / 'scripts/refresh-defect-statuses.sh', '--extract-only', '--format', 'json',
                                 '--repo', 'not/a-repo', '--output', os.path.relpath(output, ROOT)],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())

    def test_canonical_registry_and_inline_markers_match(self):
        self.assertTrue(reporter.load_registry(ROOT))

    def test_missing_unknown_duplicate_and_misplaced_markers_fail(self):
        guide = self.root / 'guides/test.md'
        original = guide.read_text()
        marker = '<!-- defect-ref:owner.repo:issue:19 -->'
        for text, error in (
            (original.replace(marker, ''), 'missing defect markers'),
            (original + '\n<!-- defect-ref:unknown -->\n', 'unknown or misplaced'),
            (original + '\n' + marker, 'duplicate defect marker'),
            (original.replace(marker, '') + '\n## Unrelated\n' + marker, 'unknown or misplaced'),
        ):
            with self.subTest(error=error):
                guide.write_text(text)
                with self.assertRaisesRegex(ValueError, error):
                    reporter.load_registry(self.root)

    def test_fenced_marker_examples_do_not_register_claims(self):
        guide = self.root / 'guides/test.md'
        original = guide.read_text()
        guide.write_text(original + '\n```md\n<!-- defect-ref:unknown -->\n```\n')
        self.assertEqual(len(reporter.load_registry(self.root)), 1)
        guide.write_text(original.replace('<!-- defect-ref:owner.repo:issue:19 -->', '')
                         + '\n~~~md\n<!-- defect-ref:owner.repo:issue:19 -->\n~~~\n')
        with self.assertRaisesRegex(ValueError, 'missing defect markers'):
            reporter.load_registry(self.root)


if __name__ == '__main__':
    unittest.main()
