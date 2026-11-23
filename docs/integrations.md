# Runtime integrations

Thin wrappers that run a LangGraph graph or an OpenAI Agents SDK agent and then
verify the trace with the same acceptance contract. The modules are duck-typed and do
not import either framework at import time; install the framework separately.

## LangGraph

```python
from assaystone import RuntimeGuard
from assaystone.integrations import LangGraphGuard

guard = RuntimeGuard(
    ".assaystone/contract.json",
    baseline=".",
    irreversible={"refund.create"},
    approval_callback=ask_human,
)

guarded = LangGraphGuard(guard, baseline=".")
state = guarded.invoke(graph, {"messages": [...]})
```

- `invoke` / `ainvoke` run the graph, then verify the final state.
- The state can be a LangGraph dict with `messages`, or a bare message list.
- Artifacts: pass `artifacts=...`; otherwise the wrapper replays `Edit` / `Write`
  calls against `baseline`, or uses `git_repo` when provided.
- If you own the loop, call `verify_langgraph_state(guard, state, baseline=".")`
  directly.

## OpenAI Agents SDK

```python
from agents import Runner
from assaystone import RuntimeGuard
from assaystone.integrations import run_with_verification

result = run_with_verification(
    guard,
    agent,
    "fix the failing test",
    runner=Runner,
    baseline=".",
)
```

- `run_with_verification` / `run_with_verification_async` run and verify.
- Or run yourself, then `verify_openai_result(guard, result, baseline=".")`.
- The adapter reads `RunResult.to_input_list()`, `new_items`, or `messages`.

## Semantics

- Verification happens after the run. `RuntimeGuard` enforces pass/fail/escalate;
  `enforce=False` gives shadow mode.
- For pre-action approval, use `RuntimeGuard`'s tool policies (irreversible tools +
  approval callback). These wrappers do not replace that.
- No framework import at module import; version-specific message shapes are handled by
  duck typing. New SDK shapes are welcome as fixtures.
