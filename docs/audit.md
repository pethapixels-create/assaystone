# Audit your traces

The audit is the entry point. It does not require a contract, labels, or a running
agent: give it a transcript or a trace and it reports the silent failures in it.

```bash
python3 -m assaystone demo audit
```

## Inputs

```bash
# newest transcript for the current workspace (no path required)
assaystone audit --latest claude-code
assaystone audit --latest codex

# explicit Claude Code transcript
assaystone audit ~/.claude/projects/.../<session>.jsonl --baseline .

# Codex CLI session JSONL
assaystone audit ~/.codex/sessions/.../rollout-*.jsonl --baseline .

# LangSmith / Langfuse / OpenTelemetry
assaystone audit runs.json --format langsmith --baseline .
assaystone audit trace.json --format langfuse --baseline .
assaystone audit otel.json --format otel --baseline .

# a message export (a JSON list, or an object with "messages")
assaystone audit messages.json --baseline .

# an Assaystone trace JSON
assaystone audit trace.json --format trace --baseline .

# a directory of .json / .jsonl files
assaystone audit traces/ --baseline .
```

`--format` is `auto` by default; Claude Code, Codex CLI, LangSmith, Langfuse, and
OpenTelemetry exports are detected from their shape. `--latest` finds the newest
Claude Code or Codex session whose recorded working directory contains the current
directory. Details: [importers](importers.md).

When the changes are real, prefer git:

```bash
assaystone audit session.jsonl --git-repo .
```

`--git-repo` collects tracked changes vs `HEAD` plus untracked files; it is more
reliable than replaying tool calls.

## How artifacts are recovered

For Claude Code and Codex CLI transcripts, the audit replays file operations on the
baseline:

- `Write` sets the file content.
- `Edit` applies `old_string` → `new_string` (honoring `replace_all`).
- `MultiEdit` applies its edits in order.
- Codex `apply_patch` additions, updates, deletes, and moves are applied in order.
- `Read`, `Bash`, and `exec_command` are recorded as steps; shell side effects are
  not reconstructed.

The resulting files are compared to the baseline and passed to the verifiers as
artifacts. Changes made through arbitrary shell commands (for example `rm` or `sed`)
are not reconstructed; use `--git-repo` for those.

### Replay vs workspace

The default mode replays edits on a **pre-session** baseline. If replay does not cover
every touched path, the audit assumes the baseline is the **post-session** workspace
and reads the current files instead. `--workspace` forces that mode; the Claude Code
Stop hook always uses it.

In workspace mode, path rules (`tests.integrity`, `diff.forbidden_paths`), syntax,
debug prints, claim-vs-evidence, and the step budget work. `diff.max_lines` and
`diff.public_api` are effectively no-ops because the pre-change content is not
available.

`--git-preimage` fixes that: it builds a temporary baseline from `HEAD` for the changed
paths and runs the diff-based checks against it. The Claude Code hook does this
automatically when the working tree has a `HEAD` commit. If the agent committed its own
changes, the pre-image is already post-session; the path rules still work, but diff-size
and public-API checks are less meaningful.

## Default rules

The audit runs a contract with `fail_fast=false`, so it reports every finding, not
just the first:

| Rule | Severity | Catches |
|---|---|---|
| `diff.syntax` | critical | broken Python |
| `tests.integrity` | high | test files modified or deleted (including nested `server/tests/`) |
| `diff.forbidden_paths` | high | CI/config edits |
| `evidence.claims` | high | success claims contradicted by recorded test evidence |
| `diff.public_api` | medium | removed or changed public API |
| `quality.no_debug_prints` | medium | debug prints left in changed code |
| `diff.max_lines` | low | oversized patches |
| `budget.steps` | low | runaway loops |

`--run-tests` adds `tests.pass` (it executes the repository's test command). It is off
by default because the audit should be safe to run on any checkout. The command runs
in a temporary copy of the baseline, not a sandbox; only audit repositories you trust.

## Test evidence

For a `Bash` / `Shell` / Codex `exec_command` step that runs a known test runner
(`pytest`, `npm test`, `go test`, and similar), the audit infers `test_exit_code` from
the step's success
flag and structured output. Ambiguous output leaves the evidence unset instead of
guessing. This lets `evidence.claims` catch "all tests pass" when the recorded run
says otherwise; pass explicit evidence when you have it.

## Output

```
Assaystone audit
baseline: /path/to/repo
traces: 1 (0 clean, 1 with findings)

audit-demo-session  changed: pricing/discounts.py, tests/test_discounts.py
  HIGH     tests.integrity          tests/test_discounts.py (modified)

summary: 0 critical, 1 high, 0 medium, 0 low
```

- `--json` prints the report and the suggested contract as JSON.
- `--sarif PATH` writes SARIF 2.1.0 for GitHub code scanning.
- `--junit PATH` writes a JUnit XML suite for CI systems.
- `--no-evidence` keeps raw evidence (test output, tool results) out of machine
  reports. Human output never prints raw evidence.
- `--fail-on high` exits `1` only for critical/high findings; `--fail-on none` always
  exits `0` (report-only mode). Default is `any`.
- `--write-contract PATH` writes the suggested contract. The same verifiers run in CI
  and at runtime; audit findings become the acceptance criteria.

Exit codes: `0` clean, `1` findings, `2` the input could not be audited.

## In CI

```bash
assaystone audit agent-transcripts/ --baseline . \
  --sarif results.sarif --junit results.xml --fail-on high
```

For pull requests, audit the diff instead:

```bash
assaystone audit trace.json --git-repo . --fail-on high
```

The audit is deliberately read-only. It never edits the repository; the only write is
an explicit `--write-contract` (and the hook's local cache).

## Hook

```bash
assaystone hook install claude-code --mode warn
```

The Stop hook runs the same audit after each Claude Code turn. See [hooks](hooks.md).

## Limitations

- Reconstructing artifacts from transcripts depends on the tool names and argument
  shapes; custom tools may need an adapter or `--git-repo`.
- Arbitrary shell side effects are not replayed. Codex `apply_patch` is replayed, but
  other `exec_command` file writes require `--git-repo`.
- `--latest` is local-only and reads transcript headers under `~/.claude/projects` and
  `~/.codex/sessions`; set `ASSAYSTONE_CLAUDE_ROOT` or `ASSAYSTONE_CODEX_ROOT` to
  override those locations.
- Test evidence combines the tool's success flag with output summaries. It can still
  be ambiguous; when in doubt, record evidence explicitly.
- The default rules are code-centric. Ops contracts use the `ops.*` pack at runtime
  and in backtests.
- LangSmith / Langfuse importers are heuristic; see [importers](importers.md) for the
  supported shapes and limitations.

The Claude Code Stop hook runs the same audit at the end of every session; see
[hooks](hooks.md).
