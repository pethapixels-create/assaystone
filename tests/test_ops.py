import unittest
from pathlib import Path

from assaystone.backtest import backtest
from assaystone.contract import Contract
from assaystone.model import load_traces
from assaystone.runner import run_contract
from assaystone.runtime import ApprovalRequired, ContractFailed, RuntimeGuard

REPO = Path(__file__).resolve().parent.parent
OPS = REPO / "examples" / "ops_agent"


class OpsPackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traces = load_traces(OPS / "traces")
        cls.by_id = {trace.id: trace for trace in cls.traces}
        cls.amount_only = Contract.load(OPS / "contracts" / "amount_only.json")
        cls.hardened = Contract.load(OPS / "contracts" / "hardened.json")
        cls.baseline = OPS / "baseline"

    def test_backtest_gap(self):
        amount_only = backtest(self.amount_only, self.traces, self.baseline)
        hardened = backtest(self.hardened, self.traces, self.baseline)
        self.assertEqual(
            (len(amount_only.defects), amount_only.caught, amount_only.escaped),
            (4, 0, 4),
        )
        self.assertEqual(
            (len(hardened.defects), hardened.caught, hardened.escaped),
            (4, 4, 0),
        )
        self.assertEqual(hardened.false_alarms, 0)

    def test_clean_trace_passes(self):
        result = run_contract(self.hardened, self.by_id["t01-correct"], self.baseline)
        self.assertEqual(result.verdict, "pass", result.first_failure)

    def test_runtime_approval_required(self):
        guard = RuntimeGuard(
            self.hardened,
            self.baseline,
            irreversible={"refund.create"},
            approval_callback=lambda *_: False,
        )
        session = guard.session(task="deny")
        with self.assertRaises(ApprovalRequired):
            session.call("refund.create", {"amount_cents": 4000}, lambda: "refunded")

    def test_runtime_contract_failure(self):
        guard = RuntimeGuard(
            self.hardened,
            self.baseline,
            irreversible={"refund.create"},
            approval_callback=lambda *_: True,
        )
        session = guard.session(task="over limit")
        session.call(
            "refund.create",
            {"order_id": "O-1001", "amount_cents": 12000},
            lambda: "refunded",
        )
        with self.assertRaises(ContractFailed):
            session.finish(artifacts=self.by_id["t02-over-limit"].artifacts)

    def test_runtime_clean_pass(self):
        guard = RuntimeGuard(
            self.hardened,
            self.baseline,
            irreversible={"refund.create"},
            approval_callback=lambda *_: True,
        )
        session = guard.session(task="clean")
        session.call(
            "refund.create",
            {"order_id": "O-1001", "amount_cents": 4000},
            lambda: "refunded",
        )
        result = session.finish(artifacts=self.by_id["t01-correct"].artifacts)
        self.assertEqual(result.verdict, "pass", result.first_failure)

    def test_shadow_mode_does_not_raise(self):
        guard = RuntimeGuard(self.hardened, self.baseline, enforce=False)
        session = guard.session(task="shadow")
        session.call(
            "refund.create",
            {"order_id": "O-1001", "amount_cents": 12000},
            lambda: "refunded",
        )
        result = session.finish(artifacts=self.by_id["t02-over-limit"].artifacts)
        self.assertEqual(result.verdict, "fail")


if __name__ == "__main__":
    unittest.main()
