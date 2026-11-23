# LangSmith and Langfuse importers

The audit accepts observability exports directly. Both importers rebuild the files
changed by tool runs, so the same rules that work on Claude Code transcripts work on
production traces.

## LangSmith

Export runs as JSON or JSONL. Supported shapes:

- `{"runs": [...]}`
- a JSON list of runs
- a nested run tree with `child_runs`
- JSONL, one run per line

Runs are grouped by `trace_id` (or the file stem). A run is treated as a tool when
`run_type` is `"tool"` / `"function"`, or when its `inputs` contain file/command keys.
The importer replays `Write` / `Edit` / `MultiEdit` inputs and uses the last LLM
output as the final message.

```bash
assaystone audit runs.json --format langsmith --baseline .
```

## Langfuse

Supported shapes:

- `{"data": [trace, ...]}`
- a list of traces with `observations`
- a single trace with `observations`
- a flat observation list grouped by `traceId`
- JSONL

Spans whose name or input looks like a tool are replayed; `GENERATION` observations
are used for the final message. `level: "ERROR"` marks a step as failed.

```bash
assaystone audit trace.json --format langfuse --baseline .
```

Auto-detection is on by default; `--format` forces an importer.

## OpenTelemetry GenAI

Accepts OTLP JSON (`{"resourceSpans": [...]}`, `{"scopeSpans": [...]}`,
`{"spans": [...]}`, or a flat span list). Tool spans are detected from
`gen_ai.operation.name` / `gen_ai.tool.name`; arguments come from
`gen_ai.tool.call.arguments`; results from `gen_ai.tool.call.result`. Final text comes
from `gen_ai.output.messages` / `gen_ai.response.text`; the task comes from
`gen_ai.input.messages` / `gen_ai.prompt`.

```bash
assaystone audit otel.json --format otel --baseline .
```

OTel attribute shapes vary by exporter; this reader handles the standard OTLP JSON
encoding (`stringValue`, `intValue`, `arrayValue`, `kvlistValue`, ...). New exporter
variants are welcome as fixtures.

## What is reconstructed

The importer extracts tool records `(name, args, result, ok)`, then applies:

- `Write` / `write_file` / `create_file`: replace the file.
- `Edit` / `str_replace`: apply old → new.
- `MultiEdit`: apply edits in order.
- `delete_file`: mark deleted.

The resulting files are diffed against the baseline and passed to the verifiers. Bash
side effects are not replayed; use `--git-repo` when that matters.

## Limitations

- If the observability tool stores only LLM messages and not tool runs, the importer
  cannot recover artifacts. Export tool/span observations.
- Custom tool names need inputs with `file_path` / `path` / `command` / `old_string` /
  `new_string` / `content`, or use a trace JSON with explicit artifacts.
- Run and observation shapes vary by version; `--format` plus a fixture is the
  supported path. Contributions for new shapes are welcome.
- Everything runs locally; no data leaves the machine.

## Fixtures

See `examples/importers/` for a LangSmith run list, a Langfuse trace, and an OTel span
set of the same test-tampering trajectory.
