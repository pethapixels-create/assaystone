"""Contract runner: cheapest sufficient verifier first; pass / fail / escalate."""
from __future__ import annotations

import time
from pathlib import Path

from .contract import Contract
from .model import ESCALATE, FAIL, PASS, RunResult, Trace, Verdict
from .verifiers import REGISTRY, Verifier, VerifyContext
from .workspace import Workspace


def run_contract(contract: Contract, trace: Trace, baseline: str | Path) -> RunResult:
    started = time.perf_counter()
    verdicts: list[Verdict] = []
    total_cost = 0.0
    overall = PASS
    first_failure: str | None = None

    for spec in contract.verifiers:
        if spec.name not in REGISTRY:
            raise KeyError(f"unknown verifier in contract: {spec.name}")

    with Workspace(baseline) as workspace:
        workspace.apply(trace.artifacts)
        ctx = VerifyContext(
            trace=trace,
            workspace=workspace,
            baseline=Path(baseline).resolve(),
            test_command=contract.test_command,
        )

        specs = sorted(contract.verifiers, key=lambda item: REGISTRY[item.name].cost_usd)
        for spec in specs:
            verifier: Verifier = REGISTRY[spec.name]()

            if total_cost + verifier.cost_usd > contract.max_verification_cost_usd:
                overall = ESCALATE
                first_failure = f"verification budget exceeded before {verifier.name}"
                break

            check_started = time.perf_counter()
            try:
                ok, reasons, evidence = verifier.check(ctx, spec.params)
            except Exception as exc:  # noqa: BLE001 - a crashing verifier must fail closed
                ok, reasons, evidence = None, [f"verifier crashed: {exc!r}"], []
            duration_ms = (time.perf_counter() - check_started) * 1000

            verdicts.append(
                Verdict(
                    verifier=verifier.name,
                    layer=verifier.layer,
                    ok=ok,
                    reasons=reasons,
                    evidence=evidence,
                    cost_usd=verifier.cost_usd,
                    duration_ms=duration_ms,
                )
            )
            total_cost += verifier.cost_usd

            if ok is None:
                if spec.required:
                    if overall != FAIL:
                        overall = ESCALATE
                    if first_failure is None:
                        first_failure = f"{verifier.name}: {reasons[0] if reasons else 'unresolved'}"
                    if contract.fail_fast:
                        break
                continue

            if ok is False and spec.required:
                overall = FAIL
                if first_failure is None:
                    first_failure = f"{verifier.name}: {reasons[0] if reasons else 'failed'}"
                if contract.fail_fast:
                    break

    return RunResult(
        trace_id=trace.id,
        contract=contract.name,
        verdict=overall,
        verdicts=verdicts,
        cost_usd=total_cost,
        duration_ms=(time.perf_counter() - started) * 1000,
        first_failure=first_failure,
    )
