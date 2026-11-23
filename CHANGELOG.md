# Changelog

## 0.3.0

- `assaystone audit`: Claude Code transcripts, message exports, trace JSON
- LangSmith, Langfuse, and OpenTelemetry GenAI importers (`--format`, auto-detect)
- Claude Code Stop hook (`assaystone hook install claude-code`), warn/block, dedupe,
  and `.assaystone/hook.json` ignore rules
- SARIF 2.1.0 and JUnit output for `audit` and `verify`
- shared tool-call replay and test-evidence inference
- `--workspace` / post-session fallback: current files when replay cannot cover edits
- `--git-preimage`: HEAD-based baseline for post-session diff checks; the hook uses it
  when available
- `tests.integrity` matches nested test dirs (`server/tests/`, `demo2/server/tests/`)
- default audit rules, severity levels, JSON output, `--fail-on`, suggested contract
- `Contract.from_dict` / `to_dict`; `fail_fast=False` aggregates all verdicts
- `record` accepts Claude Code transcripts, importers, and trace JSON
- packaged `demo_data` so `pip install assaystone && assaystone demo` works
- `--no-evidence` to keep raw evidence out of machine reports
- third-party verifier packs via `assaystone.verifiers` entry points
- CI matrix 3.10–3.12 plus a wheel build/install demo job
- GitHub Action install input; project metadata and license files

## 0.2.0

- runtime gate: irreversible-tool policies, approval callbacks, contract enforcement,
  shadow mode
- ops/refund verifier pack and `assaystone demo ops`
- LangGraph adapter
- runtime, adapter, verifier, and contract reference docs

## 0.1.0

- acceptance contracts and a cost-ordered verifier ladder
- `pass / fail / escalate` verdicts with reasons and evidence refs
- mutation testing and backtesting over recorded traces
- Claude Agent SDK / OpenAI-style / LangGraph message adapters and `artifacts_from_git`
- `assaystone init --ci`, `assaystone record`, `verify --json`, `verify --github`
- pytest plugin (one item per trace) and a composite GitHub Action
- scorecard, Failure Zoo seed, and launch docs

## 0.0.1

- initial code/test verifier pack and demo
