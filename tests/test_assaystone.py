import unittest
from pathlib import Path

from assaystone.backtest import backtest
from assaystone.contract import Contract
from assaystone.model import Artifact, Trace
from assaystone.mutate import generate_mutants
from assaystone.runner import run_contract
from assaystone.workspace import Workspace
from examples.code_agent import scenarios

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples" / "code_agent"


class AssaystoneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = EXAMPLES / "baseline"
        cls.naive = Contract.load(EXAMPLES / "contracts" / "naive.json")
        cls.hardened = Contract.load(EXAMPLES / "contracts" / "hardened.json")
        cls.traces = scenarios.write_traces()
        cls.by_id = {trace.id: trace for trace in cls.traces}

    def test_trace_roundtrip(self):
        trace = self.by_id["t01-correct"]
        clone = Trace.from_dict(trace.to_dict())
        self.assertEqual(clone.id, trace.id)
        self.assertEqual(clone.artifacts[0].path, trace.artifacts[0].path)
        self.assertEqual(clone.labels.verdict, "pass")

    def test_correct_patch_passes_both_contracts(self):
        for contract in (self.naive, self.hardened):
            result = run_contract(contract, self.by_id["t01-correct"], self.baseline)
            self.assertEqual(result.verdict, "pass", result.first_failure)

    def test_test_tampering_escapes_naive_but_not_hardened(self):
        trace = self.by_id["t03-test-tampering"]
        self.assertEqual(run_contract(self.naive, trace, self.baseline).verdict, "pass")
        hardened = run_contract(self.hardened, trace, self.baseline)
        self.assertEqual(hardened.verdict, "fail")
        self.assertIn("tests.integrity", hardened.first_failure or "")

    def test_forbidden_path_escapes_naive_but_not_hardened(self):
        trace = self.by_id["t04-forbidden-path"]
        self.assertEqual(run_contract(self.naive, trace, self.baseline).verdict, "pass")
        hardened = run_contract(self.hardened, trace, self.baseline)
        self.assertEqual(hardened.verdict, "fail")
        self.assertIn("diff.forbidden_paths", hardened.first_failure or "")

    def test_debug_print_escapes_naive_but_not_hardened(self):
        trace = self.by_id["t05-debug-print"]
        self.assertEqual(run_contract(self.naive, trace, self.baseline).verdict, "pass")
        hardened = run_contract(self.hardened, trace, self.baseline)
        self.assertEqual(hardened.verdict, "fail")
        self.assertIn("quality.no_debug_prints", hardened.first_failure or "")

    def test_backtest_metrics(self):
        naive = backtest(self.naive, self.traces, self.baseline)
        hardened = backtest(self.hardened, self.traces, self.baseline)
        self.assertEqual((len(naive.defects), naive.caught, naive.escaped), (4, 1, 3))
        self.assertEqual((len(hardened.defects), hardened.caught, hardened.escaped), (4, 4, 0))
        self.assertEqual(hardened.false_alarms, 0)

    def test_mutation_generates_policy_mutants(self):
        mutants = generate_mutants(self.by_id["t01-correct"], self.baseline, max_total=18)
        operators = {mutant.operator for mutant in mutants}
        for expected in (
            "insert_print",
            "touch_forbidden_file",
            "delete_test_method",
            "weaken_assert",
        ):
            self.assertIn(expected, operators)

    def test_workspace_rejects_path_traversal(self):
        with Workspace(self.baseline) as workspace:
            with self.assertRaises(ValueError):
                workspace.apply([Artifact("../escape.py", "print('x')")])


if __name__ == "__main__":
    unittest.main()
