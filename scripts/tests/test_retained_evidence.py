import hashlib
import json
import pathlib
import unittest

from scripts.probe_evidence import parse_log

ROOT = pathlib.Path(__file__).resolve().parents[2]


class RetainedEvidenceTests(unittest.TestCase):
    def test_probe_details_skip_reasons_and_topology_reconcile_with_raw_logs(self):
        release = json.loads((ROOT / 'notes/evidence/release-27.2/probe-results.json').read_text())
        runtime = json.loads((ROOT / 'notes/evidence/runtime-current.json').read_text())
        current = json.loads((ROOT / 'notes/current-state.json').read_text())
        for name, lane in release['lanes'].items():
            source = lane['sources'][0]
            data = (ROOT / source['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), source['sha256'])
            parsed = parse_log(data.decode())
            self.assertEqual(parsed['results'], lane['results'])
            self.assertEqual(parsed['skipReasons'], lane['skipReasons'])
            flat = next(row for row in runtime['lanes'] if row['mode'] == name)
            baseline = current['probeBaselines'][f'tool-hosted-current-{name}']
            for key in ('tests', 'skipped', 'failures', 'osVersion', 'osBuild', 'xcodeBuild', 'observedAt'):
                self.assertEqual(flat[key], lane['topology'][key])
                self.assertEqual(flat[key], baseline[key])
            self.assertNotIn('contextSize', flat)
            self.assertTrue(lane['runDirectory'])
            self.assertIn('excludedTests', lane)

    def test_mpp_availability_definitions_are_retained(self):
        evidence = json.loads((ROOT / 'notes/evidence/release-27.2/mpp-header-provenance.json').read_text())
        header = next(row for row in evidence['headers'] if row['path'].endswith('MPPTensorOpsAvailability.h'))
        self.assertTrue(any('#define __TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_26_2' in line for line in header['availability']))
        self.assertTrue(any('#define __TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_27_0' in line for line in header['availability']))

    def test_drift_includes_protocol_requirement_accessor_and_inlined_id(self):
        evidence = json.loads((ROOT / 'notes/evidence/release-27.2/interface-drift.json').read_text())
        frameworks = {row['framework']: row['changes'] for row in evidence['frameworks']}
        evaluations = frameworks['Evaluations']
        self.assertTrue(any(c.get('after', {}).get('declaration') == 'var name: Swift.String' for c in evaluations))
        self.assertTrue(any(c['kind'] == 'modified' and 'reportMetadata' in c['after']['declaration'] for c in evaluations))
        intents = frameworks['AppIntents']
        self.assertFalse(any(c['kind'] == 'removed' and 'struct AssistantSchema ' in c['before']['declaration'] for c in intents))
        self.assertTrue(any('CustomReaction' in c.get('after', {}).get('body', '') for c in intents))
