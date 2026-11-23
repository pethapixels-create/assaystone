# Importer fixtures

Two synthetic exports of the same test-tampering trajectory:

- `langsmith_runs.json` — a LangSmith run list (`run_type`, `inputs`, `outputs`,
  `trace_id`).
- `langfuse_trace.json` — a Langfuse trace export with observations.
- `otel_trace.json` — OTLP GenAI spans with `gen_ai.*` attributes.

```bash
assaystone audit examples/importers/langsmith_runs.json \
  --format langsmith --baseline examples/audit/baseline
assaystone audit examples/importers/langfuse_trace.json \
  --format langfuse --baseline examples/audit/baseline
assaystone audit examples/importers/otel_trace.json \
  --format otel --baseline examples/audit/baseline
```

The importer replays the `Edit` tool calls on the baseline, reconstructs the changed
files, and reports `tests.integrity`.
