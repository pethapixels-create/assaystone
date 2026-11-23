"""LangGraph runtime integration.

The adapter is duck-typed: it accepts a LangGraph state dict (or a bare message
list) and a graph with ``invoke`` / ``ainvoke``. It never imports LangGraph.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters.messages import from_langgraph
from ..model import RunResult, Trace
from ..runtime import RuntimeGuard
from .common import artifacts_for_trace


def trace_from_langgraph_state(
    state: Any,
    *,
    artifacts: list | None = None,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    task: str = "",
    trace_id: str | None = None,
) -> Trace:
    trace = from_langgraph(
        state,
        artifacts=artifacts or [],
        task=task,
        trace_id=trace_id,
    )
    if artifacts is None:
        trace.artifacts = artifacts_for_trace(trace, baseline=baseline, git_repo=git_repo)
    return trace


def verify_langgraph_state(
    guard: RuntimeGuard,
    state: Any,
    *,
    artifacts: list | None = None,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    task: str = "",
    trace_id: str | None = None,
) -> RunResult:
    trace = trace_from_langgraph_state(
        state,
        artifacts=artifacts,
        baseline=baseline,
        git_repo=git_repo,
        task=task,
        trace_id=trace_id,
    )
    return guard.verify(trace)


class LangGraphGuard:
    """Run a LangGraph graph, then verify the final state against a contract."""

    def __init__(
        self,
        guard: RuntimeGuard,
        *,
        baseline: str | Path | None = None,
        git_repo: str | Path | None = None,
    ):
        self.guard = guard
        self.baseline = baseline
        self.git_repo = git_repo

    def verify(self, state: Any, *, artifacts: list | None = None) -> RunResult:
        return verify_langgraph_state(
            self.guard,
            state,
            artifacts=artifacts,
            baseline=self.baseline,
            git_repo=self.git_repo,
        )

    def invoke(self, graph: Any, input: Any, **kwargs: Any) -> Any:
        state = graph.invoke(input, **kwargs)
        self.verify(state)
        return state

    async def ainvoke(self, graph: Any, input: Any, **kwargs: Any) -> Any:
        state = await graph.ainvoke(input, **kwargs)
        self.verify(state)
        return state
