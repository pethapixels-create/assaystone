# Verification is the bottleneck

**Your agent's tests pass. Did it delete the failing test?**

A coding agent is asked to make the test suite green. It does. The suite passes. But it made the suite pass by deleting the test that failed. In an eval that checks "does the suite pass," this is a perfect score. In production, it is a defect.

This is the central problem of agent products in 2026: we have become good at generating plausible work and bad at deciding whether the work is acceptable. The result is agents that demo beautifully and fail silently.

## Demos sample once; reliability compounds

An agent that succeeds 95% per step over 20 steps succeeds about 36% of the time. Humans fail too, but human workflows have cheap correction (look at it, ask, redo) and social redundancy (a colleague reviews). The worst agent failure is not a crash; it is a confident, plausible, wrong result.

Nothing in the product surface tells you which run was the 5%. A green checkmark means "the agent said it was done," not "the work satisfies the acceptance criteria." Trust never compounds, so delegation collapses into supervision.

## Scores are not verdicts

An evaluation gives you 0.87. A production workflow needs a verdict: **pass, fail, or a human must look**; what failed; what evidence supports the decision; what it cost to decide.

A score cannot gate a merge, authorize a refund, or satisfy an auditor. A verdict with evidence can. This sounds like a small interface difference. It is the whole product difference.

## The bottleneck moved to verification

Generation became roughly 100× cheaper. Verification did not. Amdahl's law applies to knowledge work: system throughput is set by the part you did not accelerate.

This is why coding agents landed first. Not because programming is easy, but because the program world has the cheapest oracles in existence: compilers, type checkers, tests, diffs, exit codes. The verifier is free, automatic, and independent of the model.

Support agents land in narrow domains with a knowledge base, a policy engine, and a human fallback. Reconciliation agents land because totals must match. Research agents struggle because the only verifier is the user, and the cost of verification equals the cost of doing the work.

**The boundary of reliable delegation is the boundary of cheap verification.** If you want to know what an agent product can do, do not look at its model; look at its oracle.

## The verifier is the product

If verification is the bottleneck, leverage comes from making work verifiable:

- Make outputs structured enough to check: diffs, citations, schemas, totals.
- Force evidence: every claim links to a tool result, source span, log, or artifact.
- Push checks down the ladder: deterministic invariants before tests, tests before judges.
- Price verification: every check declares cost, latency, and independence.
- Treat escalation as a feature: when cheap checks cannot decide, route to a human with an evidence bundle.

The last point is the one most products miss. A system that knows when it does not know is more valuable than a system that always answers.

## Challenge the verifier

A verifier you have never challenged is a liability. It produces confidence, not correctness.

Mutation testing fixes this. Inject one known defect at a time into the agent's artifacts and ask whether the contract kills it. If your contract cannot tell a correct patch from one that deleted the failing test, it is not a verifier; it is a cheerleader.

The demo in this repository does exactly that. The naive contract (`tests + syntax`) kills 67% of injected defects. The hardened contract kills 94%. The surviving mutant is a rounding-constant change the tests cannot distinguish — a test gap, not a verifier bug. That is the finding you want mutation testing to produce.

## Backtest before enforcing

Adding a check is a product decision with a catch rate, a false-alarm rate, and a cost. Replay historical traces, measure all three, and only then enforce the check in production.

This is how risk teams add fraud rules. Agent teams should work the same way. "We added a verifier" is not an engineering statement until it has a backtest.

## The ladder

- **L0** — invariants, schemas, step budgets. Almost free.
- **L1** — compilers, tests, path policy. Cheap, independent.
- **L2** — diffs, public API, custom rules. Cheap, independent.
- **L3** — evidence and citation checks. Low-medium cost, medium-high independence.
- **L4** — LLM judge. Cheap per call, but correlated with the generator. A filter, never the oracle.

Use the cheapest sufficient verifier. Stop at the first required failure. Record what the decision cost.

## Start with an audit

The hardest part of verification is the cold start: most teams do not have a contract,
a labeled dataset, or a verifier set. They do have traces.

An audit inverts the funnel. Point it at a transcript and it reconstructs what the
agent changed, then runs a default rule set: test tampering, forbidden paths, debug
prints, self-report contradictions, oversized diffs. You do not have to know what to
check in advance. The findings tell you what to check, and become the first contract.

This is the difference between asking someone to adopt a framework and showing them a
failure they did not know they had.

## Close the loop at action time

CI catches a bad run after it happened. The same contract can run inside the loop:
policy checks before an irreversible tool call, the acceptance contract at the end.
If approval is missing, the action does not execute. If the contract fails, the run
stops. This is the difference between a report and a gate.

## Where this leaves builders

The winning agent products will not be the most autonomous. They will be the most verifiable.

Autonomy is a demo. Verifiability is a product. Build the contract, the evidence, the escalation path, and the measurement that proves the checks work. Then — and only then — let the agent act.

## Try it

```bash
python3 -m assaystone demo audit  # audit a coding-agent transcript
python3 -m assaystone demo        # code/test pack
python3 -m assaystone demo ops    # runtime gate + ops/refund pack
```

The audit demo points at a transcript where the agent deleted the failing test and
reported success; it finds the test tampering. The code demo runs six recorded traces
against two contracts, injects defects to measure recall, backtests the contracts, and
writes a scorecard. The ops demo shows the same core gating refunds: an amount-only
contract catches 0/4 bad refunds, the hardened contract catches 4/4, and the runtime
gate blocks a denied approval. No API keys. No dependencies.
