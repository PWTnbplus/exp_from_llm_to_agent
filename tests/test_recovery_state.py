"""Regression tests for stateful Codex handoffs; require no APIs/network."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'recovery_state.py'
spec = importlib.util.spec_from_file_location('recovery_state_test', SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def finding(self, priority='P1'):
        return {'severity': priority, 'fingerprint': 'same-underlying-defect',
                'title': 'Frozen plan mutation',
                'evidence': 'src/runners/llm_only.py:42 modifies actions after feedback',
                'remediation': 'Freeze immutable plan; test observation swapping'}

    def test_bootstrap_idempotent_historical_audits(self):
        folder = self.root / 'docs/audits/cycle-20261008-01'
        folder.mkdir(parents=True)
        (folder / 'audit.json').write_text(json.dumps({'review': {'findings': [self.finding()]}}))
        count, ledger = r.ingest_audits(self.root)
        self.assertEqual(count, 1)
        self.assertEqual(len(ledger['issues']), 1)
        count, ledger = r.ingest_audits(self.root)
        self.assertEqual(count, 0)
        self.assertEqual(len(ledger['issues']), 1)
        self.assertIn('Frozen plan mutation', (self.root / r.REPORT_PATH).read_text(encoding='utf-8'))
        self.assertIn('Next issue:', (self.root / r.HANDOFF_PATH).read_text(encoding='utf-8'))

    def test_omitted_issue_cannot_implicitly_close(self):
        ledger = r.new_state()
        ids = r.ingest_findings(ledger, [self.finding()], source='cycle-1')
        r.save(self.root, ledger)
        r.ingest_review(self.root, {'findings': [], 'resolutions': []},
                        test={'exit_code': 0, 'command': ['python', '-m', 'pytest', '-q']}, source='cycle-2')
        self.assertEqual(r.get_issue(r.load(self.root), ids[0])['status'], 'OPEN')

    def test_review_verification_requires_host_pass(self):
        ledger = r.new_state()
        issue_id = r.ingest_findings(ledger, [self.finding()], source='cycle-1')[0]
        r.save(self.root, ledger)
        report = {'findings': [], 'resolutions': [{'id': issue_id, 'verdict': 'VERIFIED',
                 'evidence': 'tests/test_llm_isolation.py::test_observation_swap passed'}]}
        r.ingest_review(self.root, report, test={'exit_code': 1, 'command': ['python','-m','pytest','-q']}, source='cycle-2')
        self.assertEqual(r.get_issue(r.load(self.root), issue_id)['status'], 'OPEN')
        r.ingest_review(self.root, report, test={'exit_code': 0, 'command': ['python','-m','pytest','-q']}, source='cycle-3')
        issue = r.get_issue(r.load(self.root), issue_id)
        self.assertEqual(issue['status'], 'VERIFIED')
        self.assertIn('pytest', issue['verification']['command'])

    def test_live_finding_prevents_simultaneous_verification(self):
        ledger = r.new_state()
        issue_id = r.ingest_findings(ledger, [self.finding()], source='cycle-1')[0]
        r.save(self.root, ledger)
        r.ingest_review(self.root, {'findings': [self.finding()],
              'resolutions': [{'id': issue_id, 'verdict': 'VERIFIED', 'evidence': 'contradictory'}]},
              test={'exit_code': 0, 'command': ['python','-m','pytest','-q']}, source='cycle-2')
        self.assertEqual(r.get_issue(r.load(self.root), issue_id)['status'], 'OPEN')

    def test_verified_regression_reopens_same_issue_id(self):
        ledger = r.new_state()
        issue_id = r.ingest_findings(ledger, [self.finding()], source='cycle-1')[0]
        r.update_status(ledger, issue_id, 'VERIFIED', reason='host proof', evidence='passed test',
                        proof_command='python -m pytest -q', host_test_passed=True)
        r.ingest_findings(ledger, [self.finding()], source='cycle-3')
        self.assertEqual(len(ledger['issues']), 1)
        self.assertEqual(r.get_issue(ledger, issue_id)['status'], 'OPEN')
        self.assertIsNone(r.get_issue(ledger, issue_id)['verification'])

    def test_priority_and_blocked_issues_persist(self):
        ledger = r.new_state()
        slower = self.finding('P2')
        faster = {'severity':'P0', 'fingerprint': 'hidden-answer',
                  'evidence':'src/oracle.py leaks ground truth', 'remediation':'Remove truth output'}
        r.ingest_findings(ledger, [slower,faster], source='review')
        self.assertEqual(r.active_issues(ledger)[0]['severity'], 'P0')
        r.update_status(ledger, r.active_issues(ledger)[0]['id'], 'BLOCKED', reason='no upstream access')
        self.assertEqual(len(r.active_issues(ledger)), 2)

    def test_manual_verify_requires_host_test(self):
        ledger = r.new_state()
        issue_id = r.ingest_findings(ledger, [self.finding()], source='review')[0]
        with self.assertRaises(ValueError):
            r.update_status(ledger, issue_id, 'VERIFIED', reason='I said done', evidence='not enough')

    def test_completed_work_inventory_persists(self):
        ledger = r.new_state()
        r.record_completed(ledger, name='NewtonBench adapter', evidence='test real simulator passed',
                           verification_command='python -m pytest tests/test_adapter.py -q', commit='abc123')
        r.save(self.root, ledger)
        r.write_reports(self.root)
        self.assertIn('NewtonBench adapter', (self.root/r.HANDOFF_PATH).read_text(encoding='utf-8'))
        self.assertIn('abc123', (self.root/r.REPORT_PATH).read_text(encoding='utf-8'))

    def test_invalid_ledger_not_overwritten(self):
        path = self.root/r.STATE_PATH
        path.parent.mkdir(parents=True)
        path.write_text('{"schema_version":999,"issues":[]}')
        with self.assertRaises(ValueError):
            r.load(self.root)


if __name__ == '__main__':
    unittest.main()

class GateSafetyTests(unittest.TestCase):
    def test_missing_gates_never_default_to_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(r.unverified_gates(Path(tmp)), list(r.GATES))

    def test_pass_requires_evidence_and_executed_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            gate=root/r.GATES_PATH
            gate.parent.mkdir(parents=True)
            gate.write_text(json.dumps({'gates': {'G0': {'status': 'PASS', 'evidence': 'file exists'}}}))
            self.assertIn('G0', r.unverified_gates(root))
            gate.write_text(json.dumps({'gates': {'G0': {'status': 'PASS', 'evidence': 'tested adapter',
                'verification_command':'python -m pytest -q'}}}))
            self.assertNotIn('G0', r.unverified_gates(root))
            self.assertIn('G1', r.unverified_gates(root))
