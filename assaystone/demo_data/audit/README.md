# Audit demo

`transcript.jsonl` is a synthetic Claude Code-style transcript. The agent fixes the
rounding bug, sees the half-cent test still fail, deletes that test, and reports
success.

```bash
python3 -m assaystone demo audit
```

Assaystone reconstructs the changed files from the `Edit` tool calls, runs the default
rule set, and reports `tests.integrity`. The baseline is a copy of
`examples/code_agent/baseline`.
