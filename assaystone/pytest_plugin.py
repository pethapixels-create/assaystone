"""pytest integration.

Auto-collect one test item per trace:

    pytest --assaystone-contract .assaystone/contract.json \\
           --assaystone-traces .assaystone/traces

Or use the fixture inside a normal test:

    def test_agent_run(assaystone):
        result = assaystone.verify("traces/t01.json")
        assert result.verdict == "pass", result.first_failure
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from .contract import Contract
from .model import Trace, load_traces
from .runner import run_contract


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("assaystone")
    group.addoption(
        "--assaystone-contract",
        dest="assaystone_contract",
        default=None,
        metavar="PATH",
        help="Path to an acceptance contract JSON file.",
    )
    group.addoption(
        "--assaystone-traces",
        dest="assaystone_traces",
        default=None,
        metavar="PATH",
        help="Trace file or directory; one pytest item is generated per trace.",
    )
    group.addoption(
        "--assaystone-baseline",
        dest="assaystone_baseline",
        default=".",
        metavar="PATH",
        help="Baseline repository used to materialize each trace.",
    )


class AssaystoneRunner:
    def __init__(self, contract_path: str | Path, baseline: str | Path = "."):
        self.contract = Contract.load(contract_path)
        self.baseline = Path(baseline)

    def verify(self, trace: str | Path | Trace) -> Any:
        if isinstance(trace, (str, Path)):
            loaded = load_traces(trace)
            if len(loaded) != 1:
                raise ValueError(f"expected exactly one trace, got {len(loaded)}")
            trace = loaded[0]
        return run_contract(self.contract, trace, self.baseline)

    def verify_all(self, path: str | Path) -> list[Any]:
        return [run_contract(self.contract, trace, self.baseline) for trace in load_traces(path)]


@pytest.fixture
def assaystone(request: pytest.FixtureRequest) -> AssaystoneRunner:
    contract = request.config.getoption("assaystone_contract")
    if not contract:
        pytest.skip("--assaystone-contract not provided")
    return AssaystoneRunner(contract, request.config.getoption("assaystone_baseline"))


class AssaystoneItem(pytest.Item):
    def __init__(self, *, trace: Trace, runner: AssaystoneRunner, **kwargs: Any):
        super().__init__(**kwargs)
        self.trace = trace
        self.runner = runner

    def runtest(self) -> None:
        result = self.runner.verify(self.trace)
        if result.verdict != "pass":
            reasons = "; ".join(result.reasons[:3])
            raise AssertionError(f"{result.verdict}: {result.first_failure or reasons}")

    def repr_failure(self, excinfo: Any, style: Any = None) -> str:
        return str(excinfo.value)

    def reportinfo(self) -> tuple[Path, int, str]:
        return self.runner.baseline, 0, f"assaystone: {self.trace.id}"


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    contract = config.getoption("assaystone_contract")
    traces = config.getoption("assaystone_traces")
    if not contract or not traces:
        return
    runner = AssaystoneRunner(contract, config.getoption("assaystone_baseline"))
    for trace in load_traces(traces):
        items.append(
            AssaystoneItem.from_parent(
                session,
                name=f"assaystone::{trace.id}",
                trace=trace,
                runner=runner,
            )
        )
