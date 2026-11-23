<p align="center"><img src="assets/logo.svg" width="88" alt="Assaystone"></p>

# Assaystone

**Your agent's tests pass. Did it delete the failing test?**

![ci](https://github.com/yellowsand1/assaystone/actions/workflows/ci.yml/badge.svg)
[![pypi](https://img.shields.io/pypi/v/assaystone)](https://pypi.org/project/assaystone/)
[![release](https://img.shields.io/github/v/release/yellowsand1/assaystone)](https://github.com/yellowsand1/assaystone/releases)
![status](https://img.shields.io/badge/status-alpha-orange)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-Apache--2.0-blue)

Assaystone audits existing agent traces for silent failures — the failures a green
test suite cannot see. Point it at a transcript; get findings and a suggested contract
in seconds. Then gate CI and runtime with the same contract, and prove the checks work
with mutation testing and backtesting.

```bash
python3 -m assaystone demo audit
```

```
audit-demo-session  changed: pricing/discounts.py, tests/test_discounts.py
  HIGH     tests.integrity          tests/test_discounts.py (modified)

summary: 0 critical, 1 high, 0 medium, 0 low
```

The agent fixed the rounding bug, then deleted the one test it still failed, and
reported success. `tests.pass` saw a green suite. The audit found the deleted test.

The rest of the loop:

```bash
python3 -m assaystone demo        # code/test verifier pack
python3 -m assaystone demo ops    # runtime gate + ops/refund pack
```

The code demo compares a naive contract (`tests + syntax`) with a hardened one:
**1/4 vs 4/4** defects caught, and mutation testing raises verifier recall from
**67% to 94%**. The ops demo catches **0/4 vs 4/4** bad refunds, and the runtime gate
blocks a denied approval and an over-limit refund.

## What a passing test suite misses

| Defect | `tests.pass` | Assaystone |
|---|---|---|
| Agent deletes the failing test | ✅ passes | ❌ `tests.integrity` |
| Agent edits CI to skip the suite | ✅ passes | ❌ `diff.forbidden_paths` |
| Agent leaves a debug print | ✅ passes | ❌ `quality.no_debug_prints` |
| Agent weakens an assertion | ✅ passes | ❌ `tests.integrity` |
| Regression in another module | ❌ fails | ❌ `tests.pass` |

Actions have the same problem. In the ops demo, an amount-only contract catches 0/4
bad refunds; policy, ledger, status, and approval checks catch 4/4.

## Why

Evaluations give you a score. Production needs a verdict: what failed, why, with
what evidence, and whether a human must look. Agents fail silently; a green test
suite is not an acceptance criterion.

The longer argument: [Verification is the bottleneck](docs/why.md).

Field note: [What 162 real Claude Code sessions say about verification](docs/case-study-2026-11.md).

## Install

Python 3.10+. No runtime dependencies.

```bash
pip install assaystone
assaystone demo audit
```

From source for contributors:

```bash
git clone https://github.com/yellowsand1/assaystone
cd assaystone
python3 -m pip install -e ".[pytest]"
python3 -m assaystone demo audit
```

## Audit your own traces

```bash
# Claude Code transcript
assaystone audit ~/.claude/projects/.../<session>.jsonl --baseline .

# LangSmith / Langfuse exports
assaystone audit runs.json --format langsmith --baseline .
assaystone audit trace.json --format langfuse --baseline .

# OpenTelemetry GenAI (OTLP JSON)
assaystone audit otel.json --format otel --baseline .

# a message export or a trace JSON
assaystone audit trace-export.json --git-repo .

# turn findings into a contract
assaystone audit session.jsonl --baseline . \
  --write-contract .assaystone/contract.json

# CI reports
assaystone audit session.jsonl --baseline . \
  --sarif results.sarif --junit results.xml

# use HEAD as the pre-session baseline for diff-size / public-API checks
assaystone audit session.jsonl --baseline . --git-preimage

# aggregate-only audit of a local Claude Code corpus
python scripts/corpus_audit.py --root ~/.claude/projects
```

Supported inputs: Claude Code `.jsonl` transcripts, LangSmith run exports, Langfuse
trace/observation exports, OpenTelemetry GenAI spans, message JSON/lists, and
Assaystone trace JSON. Importers are heuristic; `--format` forces one. For transcripts
and importers, artifacts are reconstructed from `Write` / `Edit` tool calls;
`--git-repo` is more reliable when the changes are real. If the repository is already
in its post-session state, the audit falls back to reading the current files;
`--workspace` forces that mode (the Claude Code hook uses it). Default rules: test
integrity, forbidden paths, syntax, diff size, public API, debug prints, and
claim-vs-evidence. `--run-tests` adds the test suite. `--json` is for machines;
`--sarif` / `--junit` are for CI; `--no-evidence` keeps raw evidence out of reports.
Details: [docs/audit.md](docs/audit.md) · [importers](docs/importers.md).

## Quickstart in your repo

If you already have transcripts, start with `assaystone audit` above. `init` is for
when you want a contract to gate future runs:

```bash
cd your-agent-repo
assaystone init --ci
```

This writes `.assaystone/contract.json` and a GitHub Actions workflow. The contract
includes checks for syntax, forbidden paths, test integrity, diff size, public API,
debug prints, claim-vs-evidence, and the test suite (when one is detected).

Record a trace from a framework message list:

```python
from assaystone.adapters import artifacts_from_git, from_claude_agent

trace = from_claude_agent(
    messages,
    artifacts=artifacts_from_git("."),
    task="fix the failing rounding test",
)
trace.save(".assaystone/traces/run-001.json")
```

Or from a recorded transcript:

```bash
assaystone record --transcript messages.json --git-repo . \
  --out .assaystone/traces/run-001.json
```

Verify:

```bash
assaystone verify --contract .assaystone/contract.json \
  --trace .assaystone/traces
```

Exit codes: `0` all pass, `1` at least one fail, `2` needs human review. Use `--json`
for machines, `--github` for Actions annotations.

## Integrations

### Claude Code Stop hook

```bash
assaystone hook install claude-code --mode warn
```

This merges a Stop hook into `.claude/settings.local.json` (use `--user` for global
settings). The hook audits the session transcript when Claude stops. Default is warn;
`--mode block` blocks high/critical findings. Repeated identical findings are
suppressed per session, and `.assaystone/hook.json` can ignore known-good test edits.
Details: [docs/hooks.md](docs/hooks.md), example:
[examples/hooks](examples/hooks/README.md).

### pytest

```bash
pytest --assaystone-contract .assaystone/contract.json \
       --assaystone-traces .assaystone/traces
```

One test item per trace; failures show up like normal pytest failures. Or use the
fixture:

```python
def test_agent_run(assaystone):
    result = assaystone.verify(".assaystone/traces/run-001.json")
    assert result.verdict == "pass", result.first_failure
```

### GitHub Action

```yaml
- uses: yellowsand1/assaystone@main
  with:
    contract: .assaystone/contract.json
    traces: .assaystone/traces
    install: assaystone==0.3.1   # optional; default installs the action repo
```

Failures become PR annotations; a Markdown summary is written to the job summary.

### Framework adapters

- Claude Agent SDK message streams (`from_claude_agent`)
- OpenAI-style chat/tool messages (`from_openai_agents`)
- LangGraph state dicts (`from_langgraph`)
- Generic message lists (`from_messages`)
- Runtime wrappers: [LangGraph and OpenAI Agents SDK](docs/integrations.md)
- `artifacts_from_git` collects changed files as artifacts

Adapters are duck-typed and never import the framework. Details:
[docs/adapters.md](docs/adapters.md).

### Custom verifier

```python
from assaystone import Verifier, register

@register
class NoMigrationEdits(Verifier):
    name = "policy.no_migrations"
    layer = "L1"
    cost_usd = 0.00001
    independence = "high"

    def check(self, ctx, params):
        bad = [path for path, _ in ctx.changed() if path.startswith("migrations/")]
        return (not bad, [f"migration touched: {path}" for path in bad], [])
```

Add `{"name": "policy.no_migrations"}` to the contract.

## How it works

```
recorded trace (task, tool calls, artifacts, evidence)
        │
        ▼
 acceptance contract (verifier ladder + budget + escalation)
        │
        ▼
   pass / fail / escalate  ──►  CI gate, runtime gate, human review
        │
        ├── mutate: inject labeled defects, measure verifier recall
        └── backtest: replay historical traces before enforcing a check
```

- **Trace** — what the agent did, what it produced, what evidence it left.
- **Contract** — acceptance criteria for one task type, versioned with the agent.
- **Verifier** — a cheap, independent check with a declared layer and cost.
- **Verdict** — pass, fail, or escalate with reasons and evidence refs.
- **Mutation** — inject one plausible defect at a time; did the contract kill it?
- **Backtest** — replay human-labeled traces; measure catch rate, escaped defects,
  false alarms, and cost.

## Runtime gate

The same contract can gate actions, not just CI:

```python
from assaystone.adapters import artifacts_from_git
from assaystone.runtime import RuntimeGuard

guard = RuntimeGuard(
    ".assaystone/contract.json",
    baseline=".",
    irreversible={"refund.create"},
    approval_callback=ask_human,
)

with guard.session(task="refund duplicate charge") as session:
    session.call("read_order", {"order_id": "O-1"}, read_order)
    session.call("refund.create", {"amount_cents": 4000}, do_refund)
    result = session.finish(artifacts=artifacts_from_git("."))
```

Irreversible tools are blocked unless `approval_callback` returns True. The full
contract runs at `finish`; `ContractFailed` and `EscalationRequired` stop the run.
`enforce=False` runs in shadow mode. Details: [docs/runtime.md](docs/runtime.md).

Framework wrappers: `LangGraphGuard` and `run_with_verification` for OpenAI Agents —
[docs/integrations.md](docs/integrations.md).

## The verifier ladder

| Layer | Examples | Cost | Independence |
|---|---|---|---|
| L0 | invariants, schema, step budget | ~free | high |
| L1 | compiler, tests, path policy | low | high |
| L2 | diff, public API, custom rules | low | high |
| L3 | evidence / citation checks | low-medium | medium-high |
| L4 | LLM judge (not in the default ladder) | low but correlated | low |

Use the cheapest sufficient verifier. A judge is a filter, never the oracle.

References: [built-in verifiers](docs/verifiers.md) · [contract format](docs/contracts.md).

## Comparison

| | trace audit | per-run verdict | evidence | runtime gate | mutation testing | backtesting | cost-aware ladder |
|---|---|---|---|---|---|---|---|
| promptfoo | — | ✅ | partial | — | — | — | — |
| DeepEval | — | ✅ | partial | — | — | — | — |
| Inspect AI | — | ✅ | partial | — | — | — | — |
| Guardrails AI | — | ✅ | partial | ✅ | — | — | — |
| OpenWorkProof | partial | ✅ | ✅ | ✅ | — | partial | — |
| **Assaystone** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Based on public documentation as of November 2026; corrections welcome. More
framework adapters and domain packs are next.

## Design principles

1. **Verify artifacts, not self-reports.** "All tests pass" is a claim; the recorded
   exit code and the re-run suite are evidence.
2. **Record once, verify many.** Verification is decoupled from generation, so checks
   can be replayed, backtested, and mutated.
3. **Cheapest sufficient verifier first.** Every verifier declares cost; the runner
   stops at the first required failure.
4. **Escalation is a first-class outcome.** If cheap checks cannot decide, route to a
   human with an evidence bundle.
5. **Verifiers are code, and they are tested.** Mutation testing measures recall; a
   verifier you never challenged is a liability.

## Repository layout

```
assaystone/            # library: models, runner, verifiers, adapters, audit, runtime, CLI
assaystone/demo_data/  # packaged demos (the wheel can run them)
examples/code_agent/   # baseline repo, contracts, scenarios, generated traces
examples/ops_agent/    # runtime gate + ops/refund pack
examples/audit/        # a Claude Code transcript that deletes the failing test
examples/importers/    # LangSmith / Langfuse / OTel export fixtures
examples/hooks/        # Claude Code Stop hook settings
failure_zoo/           # labeled failure corpus (seed)
docs/why.md            # the longer argument
docs/case-study-2026-11.md  # 162-session field note
docs/audit.md          # audit inputs, rules, output, limitations
docs/importers.md      # LangSmith / Langfuse / OTel formats
docs/hooks.md          # Claude Code Stop hook
docs/adapters.md       # Claude / OpenAI / LangGraph adapters
docs/integrations.md   # LangGraph / OpenAI Agents runtime wrappers
docs/verifiers.md      # built-in verifier reference
docs/contracts.md      # contract format and exit codes
docs/runtime.md        # runtime guard reference
docs/launch.md         # adoption plan
docs/release.md        # maintainer release checklist
docs/releases/         # per-version release notes
scripts/corpus_audit.py # aggregate local corpus audit
tests/                 # unit + integration tests
```

## Status and roadmap

`v0.3.1` — alpha. The core is domain-agnostic; the code/test and ops/refund packs
ship today.

- [x] audit: Claude Code transcripts, message exports, trace JSON
- [x] LangSmith / Langfuse / OpenTelemetry importers
- [x] Claude Code Stop hook (warn/block, install, dedupe, allowlist)
- [x] SARIF and JUnit output
- [x] contracts, verifier ladder, pass/fail/escalate
- [x] mutation testing and backtesting
- [x] Claude Agent SDK / OpenAI-style / LangGraph adapters, `artifacts_from_git`
- [x] pytest plugin and GitHub Action
- [x] runtime gate for irreversible actions (approvals, shadow mode)
- [x] LangGraph / OpenAI Agents runtime wrappers
- [x] ops/refund pack
- [x] git pre-image baseline for post-session diff checks
- [ ] data reconciliation and report citation packs
- [ ] verifier registry and Failure Zoo benchmark
- [ ] TypeScript port

## Contributing

The fastest way to help is to
[bring a failure case](.github/ISSUE_TEMPLATE/failure_case.md). See
[CONTRIBUTING.md](CONTRIBUTING.md) for verifier and adapter guidelines.

Maintainers: see [docs/release.md](docs/release.md) for the release checklist.

If this saves you from one silent failure, star the repo — it helps other agent teams
find it.

## Name

An *assay* determines the quality of a substance; an *assay stone* (touchstone) tests
gold. Chinese: 试金石.

## License

Apache-2.0.
