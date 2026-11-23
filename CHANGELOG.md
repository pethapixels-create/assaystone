# Changelog

## Unreleased

- LangGraph (`LangGraphGuard`) and OpenAI Agents SDK (`run_with_verification`)
  runtime wrappers
- strict, newline-only JSONL parsing; invalid lines are skipped with a warning instead
  of corrupting a record on U+0085/U+2028
- SARIF locations now point at the artifact named in the finding
- test evidence is inferred only from explicit runner commands and structured outcomes
- workspace copies skip heavy directories and refuse the home directory or filesystem
  root
- forbidden defaults narrowed to `.github/workflows/` and `.github/actions/`; debug
  prints in CLI/example/script paths are ignored
- unreadable files in a trace directory are skipped with a warning; invalid trace
  shapes are rejected before `Trace.from_dict`
- field-note manual triage: 0 confirmed test tampering in the five strongest
  candidates; the path-based rule surfaces activity, not intent
- generated GitHub workflows pin the released action tag instead of `@main`

## 0.3.1

- Claude Code hook merges git working-tree changes, capturing Bash-made edits
- audit step budget raised from 200 to 5,000 based on a 162-session field audit
- `scripts/corpus_audit.py` for read-only aggregate corpus audits
- real-session field note and release notes

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
