import asyncio
import unittest
from pathlib import Path

from assaystone.integrations import (
    LangGraphGuard,
    run_with_verification,
    run_with_verification_async,
    trace_from_langgraph_state,
    trace_from_run_result,
    verify_langgraph_state,
    verify_openai_result,
)

REPO = Path(__file__).resolve().parent.parent
BASELINE = REPO / "examples" / "audit" / "baseline"


class FakeGuard:
    def __init__(self):
        self.trace = None

    def verify(self, trace):
        self.trace = trace
        return "verified"


def openai_messages() -> list[dict]:
    return [
        {"role": "user", "content": "fix the rounding bug"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "edit_file",
                        "arguments": '{"path": "pricing/discounts.py"}',
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-1", "content": "ok"},
        {"role": "assistant", "content": "Fixed. All tests pass."},
    ]


def langgraph_state() -> dict:
    return {
        "messages": [
            {"type": "human", "content": "fix the rounding bug"},
            {
                "type": "ai",
                "content": "",
                "tool_calls": [
                    {"name": "edit_file", "args": {"path": "pricing/discounts.py"}, "id": "call-1"}
                ],
            },
            {"type": "tool", "tool_call_id": "call-1", "content": "ok"},
            {"type": "ai", "content": "Fixed. All tests pass."},
        ]
    }


class FakeResult:
    def __init__(self, messages=None):
        self._messages = messages or openai_messages()

    def to_input_list(self):
        return self._messages


class FakeGraph:
    def invoke(self, input, **kwargs):
        return langgraph_state()

    async def ainvoke(self, input, **kwargs):
        return langgraph_state()


class FakeRunner:
    def run_sync(self, agent, input, **kwargs):
        return FakeResult()


class FakeAsyncRunner:
    async def run(self, agent, input, **kwargs):
        return FakeResult()


class RuntimeIntegrationTest(unittest.TestCase):
    def test_openai_verify(self):
        guard = FakeGuard()
        output = verify_openai_result(guard, FakeResult())
        self.assertEqual(output, "verified")
        self.assertEqual(guard.trace.steps[0].tool, "edit_file")
        self.assertEqual(guard.trace.steps[0].args["path"], "pricing/discounts.py")
        self.assertEqual(guard.trace.final_message, "Fixed. All tests pass.")

    def test_langgraph_verify(self):
        guard = FakeGuard()
        output = verify_langgraph_state(guard, langgraph_state())
        self.assertEqual(output, "verified")
        self.assertEqual(guard.trace.steps[0].tool, "edit_file")
        self.assertEqual(guard.trace.steps[0].args["path"], "pricing/discounts.py")

    def test_langgraph_guard_invoke(self):
        guard = FakeGuard()
        wrapper = LangGraphGuard(guard)
        state = wrapper.invoke(FakeGraph(), {})
        self.assertIn("messages", state)
        self.assertIsNotNone(guard.trace)

    def test_langgraph_guard_ainvoke(self):
        guard = FakeGuard()
        wrapper = LangGraphGuard(guard)
        state = asyncio.run(wrapper.ainvoke(FakeGraph(), {}))
        self.assertIn("messages", state)
        self.assertIsNotNone(guard.trace)

    def test_run_with_verification(self):
        guard = FakeGuard()
        result = run_with_verification(guard, object(), "go", runner=FakeRunner())
        self.assertIsInstance(result, FakeResult)
        self.assertIsNotNone(guard.trace)

    def test_run_with_verification_async(self):
        guard = FakeGuard()
        result = asyncio.run(
            run_with_verification_async(guard, object(), "go", runner=FakeAsyncRunner())
        )
        self.assertIsInstance(result, FakeResult)
        self.assertIsNotNone(guard.trace)

    def test_artifacts_are_replayed_from_baseline(self):
        messages = [
            {"role": "user", "content": "fix"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "Edit",
                            "arguments": (
                                '{"file_path": "pricing/discounts.py", '
                                '"old_string": "    discount = int(price_cents * percent / 100)", '
                                '"new_string": "    discount = (price_cents * percent + 50) // 100"}'
                            ),
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call-1", "content": "ok"},
        ]
        trace = trace_from_run_result(FakeResult(messages), baseline=BASELINE)
        self.assertEqual({artifact.path for artifact in trace.artifacts}, {"pricing/discounts.py"})

    def test_langgraph_trace_helper(self):
        trace = trace_from_langgraph_state(langgraph_state())
        self.assertEqual(trace.agent, "langgraph")
        self.assertEqual(len(trace.steps), 1)


if __name__ == "__main__":
    unittest.main()
