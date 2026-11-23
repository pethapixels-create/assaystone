# Assaystone scorecard — ops/runtime pack

> Generated at `2026-11-23T08:09:34Z`.

## Backtest

| contract | defects | caught | escaped | false alarms | catch rate | avg cost / trace |
|---|---|---|---|---|---|---|
| `amount-only` | 4 | 0 | 4 | 0 | 0% | $0.000011 |
| `hardened` | 4 | 4 | 0 | 0 | 100% | $0.000076 |

## Runtime gate

| scenario | outcome | detail |
|---|---|---|
| approval denied | blocked | approval required for refund.create |
| over-limit refund | blocked | contract failed: ops.refund_limit: R-2: 12000 cents exceeds limit 10000 |
| correct refund | pass |  |

## Read this

- `amount-only` (JSON validity + amount conservation) catches 0/4 labeled defects: every bad refund kept the total within the order amount.
- `hardened` catches 4/4 with policy, ledger, status, and approval checks, at a fraction of a cent per trace.
- The runtime gate blocks before the action when approval is denied, and raises after the action when the contract fails.

