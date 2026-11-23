import json
import tempfile
import unittest
from pathlib import Path

from assaystone.audit import audit_traces, build_audit_contract, load_audit_traces
from assaystone.contract import Contract
from assaystone.model import load_traces
from assaystone.reports import (
    write_audit_junit,
    write_audit_sarif,
    write_junit,
    write_sarif,
)
from assaystone.runner import run_contract

REPO = Path(__file__).resolve().parent.parent
CODE = REPO / "examples" / "code_agent"
AUDIT = REPO / "examples" / "audit"


class VerifyReportsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = Contract.load(CODE / "contracts" / "hardened.json")
        cls.traces = load_traces(CODE / "traces")
        cls.results = [
            run_contract(cls.contract, trace, CODE / "baseline") for trace in cls.traces
        ]

    def test_sarif(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_sarif(Path(tmp) / "out.sarif", self.traces, self.results)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], "2.1.0")
            results = data["runs"][0]["results"]
            self.assertTrue(any(result["ruleId"] == "tests.integrity" for result in results))
            self.assertTrue(any(result["level"] == "error" for result in results))

    def test_junit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_junit(Path(tmp) / "out.xml", self.results)
            text = path.read_text(encoding="utf-8")
            self.assertIn("<testsuite", text)
            self.assertIn("t03-test-tampering", text)
            self.assertIn("<failure", text)


class AuditReportsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traces = load_audit_traces(
            AUDIT / "transcript.jsonl", baseline=AUDIT / "baseline"
        )
        cls.report = audit_traces(
            build_audit_contract(AUDIT / "baseline"),
            cls.traces,
            AUDIT / "baseline",
        )

    def test_audit_sarif(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_audit_sarif(Path(tmp) / "audit.sarif", self.report)
            data = json.loads(path.read_text(encoding="utf-8"))
            results = data["runs"][0]["results"]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["ruleId"], "tests.integrity")

    def test_audit_junit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_audit_junit(Path(tmp) / "audit.xml", self.report)
            text = path.read_text(encoding="utf-8")
            self.assertIn("tests.integrity", text)
            self.assertIn("<failure", text)


if __name__ == "__main__":
    unittest.main()
