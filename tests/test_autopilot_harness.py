"""Zero-API tests for the autonomous orchestrator safety invariants."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "autopilot.py"
spec = importlib.util.spec_from_file_location("autopilot", SCRIPT)
autopilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(autopilot)


class ParsingTests(unittest.TestCase):
    def test_reviewer_pass_valid(self):
        obj = autopilot.parse_review('{"status":"PASS","project_complete":false,"findings":[]}')
        self.assertEqual(obj["status"], "PASS")

    def test_reviewer_false_pass_blocked(self):
        with self.assertRaises(ValueError):
            autopilot.parse_review('{"status":"PASS","project_complete":true,"findings":[{"severity":"P0","evidence":"bad","remediation":"fix"}]}')

    def test_reviewer_missing_evidence_rejected(self):
        with self.assertRaises(ValueError):
            autopilot.parse_review('{"status":"FAIL","project_complete":false,"findings":[{"severity":"P1","remediation":"fix"}]}')

    def test_reviewer_narrative_rejected(self):
        with self.assertRaises(ValueError):
            autopilot.parse_review('Everything is green!')

    def test_completion_gate_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("tests/test_llm_isolation.py", autopilot.completion_inventory(Path(tmp)))

    def test_sensitive_filename(self):
        self.assertTrue(autopilot.SENSITIVE_PATH.search('.env'))
        self.assertTrue(autopilot.SENSITIVE_PATH.search('private/id_ed25519'))

    def test_sensitive_content(self):
        self.assertTrue(autopilot.SENSITIVE_CONTENT.search('-----BEGIN ' + 'OPENSSH PRIVATE KEY-----'))
        self.assertTrue(autopilot.SENSITIVE_CONTENT.search('api' + '_key = ' + '"private-invalid-example-here"'))


class GitSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        def g(*args):
            return subprocess.run(["git", *args], cwd=self.root, check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()
        self.g = g
        g("init", "-b", "main")
        g("config", "user.name", "Test")
        g("config", "user.email", "test@example.test")
        g("remote", "add", "origin", f"https://github.com/{autopilot.REPO}.git")

    def tearDown(self):
        self.tmp.cleanup()

    def test_expected_origin(self):
        autopilot.verify_origin(self.root, "origin")

    def test_wrong_origin_rejected(self):
        self.g("remote", "set-url", "origin", "https://github.com/else/another.git")
        with self.assertRaises(RuntimeError):
            autopilot.verify_origin(self.root, "origin")

    def test_create_branch_unborn_repo(self):
        autopilot.ensure_branch(self.root, autopilot.BRANCH)
        self.assertEqual(self.g("branch", "--show-current"), autopilot.BRANCH)

    def test_secret_staged_rejected(self):
        (self.root / ".env").write_text("API_KEY=not-for-commit")
        self.g("add", "-A")
        with self.assertRaises(RuntimeError):
            autopilot.check_staged_safety(self.root)

    def test_commit_without_push(self):
        autopilot.ensure_branch(self.root, autopilot.BRANCH)
        (self.root / "report.txt").write_text("Evidence\n")
        r = autopilot.commit_push(self.root, remote="origin", branch=autopilot.BRANCH,
                                  cycle=1, wip=True, push=False)
        self.assertEqual(r["status"], "COMMITTED")
        self.assertEqual(r["push"], "SKIPPED")
        self.assertTrue(self.g("rev-parse", "HEAD"))


if __name__ == "__main__":
    unittest.main()
