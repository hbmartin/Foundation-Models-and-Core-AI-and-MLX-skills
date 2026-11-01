import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('reconcile_snippets_test', ROOT / 'scripts/reconcile-snippets.py')
reconciler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconciler)


class ReconciliationTests(unittest.TestCase):
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
