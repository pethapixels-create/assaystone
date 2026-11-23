"""Duck-typed runtime integrations for agent frameworks.

These modules do not import LangGraph or the OpenAI Agents SDK. They accept the
framework objects you already have and run the same acceptance contract at the
end of a run.
"""
from .langgraph import LangGraphGuard, trace_from_langgraph_state, verify_langgraph_state
from .openai_agents import (
    run_with_verification,
    run_with_verification_async,
    trace_from_run_result,
    verify_openai_result,
)

__all__ = [
    "LangGraphGuard",
    "run_with_verification",
    "run_with_verification_async",
    "trace_from_langgraph_state",
    "trace_from_run_result",
    "verify_langgraph_state",
    "verify_openai_result",
]
