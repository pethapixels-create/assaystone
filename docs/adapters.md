# Adapters

Adapters convert a framework's message list into an Assaystone `Trace`. They are
duck-typed: they accept dicts or SDK objects and never import the framework.

```python
from assaystone.adapters import (
    artifacts_from_git,
    from_claude_agent,
    from_langgraph,
    from_messages,
    from_openai_agents,
)
```

## Claude Agent SDK

```python
trace = from_claude_agent(
    messages,
    artifacts=artifacts_from_git("."),
    task="fix the failing rounding test",
)
```

The adapter understands `AssistantMessage` text blocks, `ToolUseBlock`,
`ToolResultBlock`, and `ResultMessage.result`. `session_id` becomes the trace id when
present.

## OpenAI-style messages

```python
trace = from_openai_agents(
    messages,
    artifacts=artifacts_from_git("."),
    task="fix the failing rounding test",
)
```

Handles `tool_calls` with JSON-string `arguments` and `role="tool"` results keyed by
`tool_call_id`.

## LangGraph

```python
trace = from_langgraph(state, artifacts=artifacts_from_git("."))
```

Accepts a state dict with a `messages` key, or a bare message list. LangChain
`tool_calls` using `name`/`args`/`id` are supported.

## Generic

```python
trace = from_messages(messages, agent="my-agent", task="...")
```

Recognizes Anthropic-style content blocks (`tool_use`, `tool_result`), OpenAI-style
tool calls, and framework objects with `type` or `role`.

## Artifacts

Artifacts are the files the agent changed. `artifacts_from_git(repo)` collects tracked
changes vs `HEAD` plus untracked files:

```python
artifacts = artifacts_from_git(".")
```

You can also construct them directly:

```python
from assaystone import Artifact

artifacts = [
    Artifact("pricing/discounts.py", new_source, "modified"),
    Artifact("tests/test_old.py", "", "deleted"),
]
```

## Evidence

Evidence is the independent record the verifiers trust. For a code agent, record the
test exit code when you run the suite:

```python
trace = from_claude_agent(
    messages,
    artifacts=artifacts,
    evidence={"test_exit_code": 0},
)
```

If an agent claims "all tests pass" and no evidence is recorded, `evidence.claims`
escalates instead of guessing.

## Record from the CLI

```bash
assaystone record --transcript messages.json --git-repo . \
  --out .assaystone/traces/run-001.json
```

The transcript may be a JSON list of messages or an object with a `messages` list.

## Limitations

- Binary artifacts are skipped.
- `artifacts_from_git` needs a git repository with a `HEAD` commit.
- The adapter does not infer test results from arbitrary tool output. Pass evidence
  explicitly, or write a verifier for your tool's output format.
