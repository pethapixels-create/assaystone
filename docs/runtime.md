# Runtime gate

`RuntimeGuard` runs the same acceptance contract at the point of action. It is a
small wrapper: policy checks before a tool call, the full contract at `finish`.

## Setup

```python
from assaystone.adapters import artifacts_from_git
from assaystone.runtime import RuntimeGuard

guard = RuntimeGuard(
    ".assaystone/contract.json",
    baseline=".",
    irreversible={"refund.create"},
    approval_callback=ask_human,
    enforce=True,
)
```

- `contract` — a path or a `Contract`.
- `baseline` — the repository the trace is materialized against.
- `irreversible` — tools that require approval. They get the `require_approval`
  policy automatically.
- `policies` — per-tool overrides: `allow`, `require_approval`, `deny`.
- `approval_callback(tool, args, trace) -> bool` — must be backed by a real human or
  authorization system. Do not let the agent approve itself.
- `enforce` — when `False`, `finish` returns the verdict instead of raising. Use this
  for shadow mode.

## Session

```python
with guard.session(task="refund duplicate charge", agent="refund-agent/1.0") as session:
    session.call("read_order", {"order_id": "O-1"}, read_order)
    session.call("refund.create", {"amount_cents": 4000}, do_refund)
    session.record_evidence(test_exit_code=0)
    result = session.finish(
        artifacts=artifacts_from_git("."),
        final_message="Refunded 4000 cents.",
    )
```

- `call(tool, args, fn, reversible=True)` checks policy, optionally asks for approval,
  executes `fn`, and records the step. If `fn` is omitted, only the step is recorded —
  useful when another framework executes the tool.
- Approvals are appended to `trace.evidence["approvals"]`; `ops.approval_recorded`
  checks them.
- `finish` builds a trace, runs the contract, and enforces the verdict.

## Decisions

- `ApprovalRequired` — irreversible action without approval; `fn` did not execute.
- `PolicyDenied` — the tool is denied by policy.
- `ContractFailed` — the contract failed at finish.
- `EscalationRequired` — a verifier could not decide; a human must look.

Each exception carries `.result` when a contract ran.

## Post-hoc verification

If another framework owns the loop, adapt its messages and verify the trace:

```python
from assaystone.adapters import artifacts_from_git, from_claude_agent

trace = from_claude_agent(messages, artifacts=artifacts_from_git("."))
result = guard.verify(trace)
```

## What it does not do

The runtime gate does not run the full contract before every tool call. It enforces
per-tool policy before the action and the acceptance contract at the end. Pre-action
contract subsets, compensations, and rollback are on the roadmap.
