import unittest
from pathlib import Path

from assaystone.audit import audit_traces, build_audit_contract, load_audit_traces

REPO = Path(__file__).resolve().parent.parent
BASELINE = REPO / "examples" / "audit" / "baseline"
LANGSMITH = REPO / "examples" / "importers" / "langsmith_runs.json"
LANGFUSE = REPO / "examples" / "importers" / "langfuse_trace.json"
OTEL = REPO / "examples" / "importers" / "otel_trace.json"


class ImporterTest(unittest.TestCase):
    def _check(self, path: Path, format: str):
        traces = load_audit_traces(path, format=format, baseline=BASELINE)
        self.assertEqual(len(traces), 1)
        trace = traces[0]
        self.assertEqual(
            {artifact.path for artifact in trace.artifacts},
            {"pricing/discounts.py", "tests/test_discounts.py"},
        )
        self.assertEqual(trace.evidence.get("test_exit_code"), 0)
        self.assertIn("All tests pass", trace.final_message)
        report = audit_traces(build_audit_contract(BASELINE), traces, BASELINE)
        self.assertIn("tests.integrity", {finding.verifier for finding in report.findings})

    def test_langsmith(self):
        self._check(LANGSMITH, "langsmith")

    def test_langfuse(self):
        self._check(LANGFUSE, "langfuse")

    def test_auto_langsmith(self):
        self._check(LANGSMITH, "auto")

    def test_auto_langfuse(self):
        self._check(LANGFUSE, "auto")

    def test_otel(self):
        self._check(OTEL, "otel")

    def test_auto_otel(self):
        self._check(OTEL, "auto")


if __name__ == "__main__":
    unittest.main()
