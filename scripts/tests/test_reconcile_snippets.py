import importlib.util
import pathlib
import os
import tempfile
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('reconcile_snippets_test', ROOT / 'scripts/reconcile-snippets.py')
reconciler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconciler)


class ReconciliationTests(unittest.TestCase):
    def test_anonymous_fresh_failures_are_retained_and_rejected_before_publication(self):
        for status in ('PARSE-ERROR', 'MARKER-ERROR'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                row, prior, records = self.fixture()
                row.update(snippet_id='-', status=status, line='42')
                path = root / 'results.tsv'
                path.write_bytes(reconciler.serialize_tsv([row]))
                rows = reconciler.verifier.read_results_rows(path)
                self.assertEqual(len(rows), 1)
                ledger = root / 'notes/snippet-verification'
                ledger.mkdir(parents=True)
                previous, _, _ = self.fixture()
                old = reconciler.serialize_tsv([previous])
                (ledger / 'results.tsv').write_bytes(old)
                (ledger / 'target-provenance.json').write_text('{"records": []}')
                (root / 'toolchains.json').write_text('{}')
                with mock.patch.object(reconciler, 'ROOT', root), mock.patch.object(sys, 'argv', [
                    'reconcile-snippets.py', '--fresh', str(root), '--checked-at', '2026-11-21',
                    '--evidence', str(root / 'evidence')]), self.assertRaisesRegex(ValueError, 'fresh verification failed: guide.md:42'):
                    reconciler.main()
                self.assertEqual((ledger / 'results.tsv').read_bytes(), old)
                self.assertEqual((ledger / 'target-provenance.json').read_text(), '{"records": []}')
                self.assertFalse((root / 'evidence').exists())

    def fixture(self):
        row = {column: '-' for column in reconciler.verifier.TSV_COLUMNS}
        row.update(file='guide.md', snippet_id='id', content_hash='same', info='compile:26,27',
                   status='TOOLCHAIN-UNAVAILABLE', v26='unavailable', v27='pass')
        prior = {('guide.md', 'id'): {**row, 'v26': 'pass'}}
        records = {('guide.md', 'id'): {'content_hash': 'same', 'targets': {'26': {
            'kind': 'historical-unchanged', 'verdict': 'pass', 'sdkVersion': '26.5',
            'evidenceRevision': 'historical-sha'}}}}
        return row, prior, records

    def test_unavailable_target_keeps_only_exact_historical_provenance(self):
        row, prior, records = self.fixture()
        rows, evidence = reconciler.reconcile([row], prior, records, {'27': {'sdk_version': '27.2'}}, '2026-11-01')
        self.assertEqual(rows[0]['status'], 'VERIFIED')
        target = evidence[0]['targets']['26']
        self.assertEqual(target['evidenceRevision'], 'historical-sha')
        self.assertNotIn('checkedAt', target)
        self.assertEqual(evidence[0]['targets']['27']['checkedAt'], '2026-11-01')

    def test_changed_content_cannot_inherit_historical_verdict(self):
        row, prior, records = self.fixture()
        row['content_hash'] = 'edited'
        rows, evidence = reconciler.reconcile([row], prior, records, {'27': {'sdk_version': '27.2'}}, '2026-11-01')
        self.assertEqual(rows[0]['v26'], 'unavailable')
        self.assertEqual(rows[0]['status'], 'TOOLCHAIN-UNAVAILABLE')
        self.assertNotIn('26', evidence[0]['targets'])

    def test_failed_fresh_run_cannot_replace_ledger(self):
        row, prior, records = self.fixture();row['status'] = 'FAILED'
        with self.assertRaises(ValueError):
            reconciler.reconcile([row], prior, records, {}, '2026-11-01')

    def test_literal_tsv_quotes_and_flattened_controls_round_trip(self):
        row, _, _ = self.fixture()
        row.update(first_error='"quoted" error with "nested" quotes\tand\nnewlines', info='"leading quotes"')
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'results.tsv'
            path.write_bytes(reconciler.serialize_tsv([row]))
            actual = next(iter(reconciler.verifier.read_prior_results(path).values()))
        self.assertEqual(actual['info'], row['info'])
        self.assertIn('"quoted" error with "nested" quotes', actual['first_error'])
        self.assertNotIn('\t', actual['first_error'])
        self.assertNotIn('\n', actual['first_error'])

    def test_replace_failure_restores_ledger_and_does_not_publish_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger, provenance, evidence = [root / name for name in ('results.tsv', 'provenance.json', 'evidence.tsv')]
            ledger.write_bytes(b'original ledger')
            provenance.write_bytes(b'original provenance')
            replace = os.replace
            def fail(source, target):
                if target == provenance and pathlib.Path(source).read_bytes() == b'new provenance':
                    raise OSError('injected replace failure')
                replace(source, target)
            with mock.patch.object(reconciler.os, 'replace', side_effect=fail), self.assertRaises(OSError):
                reconciler.publish({ledger: b'new ledger', provenance: b'new provenance', evidence: b'evidence'})
            self.assertEqual(ledger.read_bytes(), b'original ledger')
            self.assertEqual(provenance.read_bytes(), b'original provenance')
            self.assertFalse(evidence.exists())
            self.assertEqual(len(list(root.iterdir())), 2)
