"""OpenAI Agents SDK runtime integration.

The adapter is duck-typed: it accepts a ``RunResult`` (or any object with
``to_input_list`` / ``new_items`` / ``messages``) and never imports the SDK
unless you ask the wrapper to run for you.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters.messages import from_openai_agents
from ..model import RunResult as AssayRunResult
from ..model import Trace
from ..runtime import RuntimeGuard
from .common import artifacts_for_trace


def _messages_from_result(result: Any) -> list[Any]:
    if hasattr(result, "to_input_list"):
        return list(result.to_input_list())
    if hasattr(result, "new_items"):
        messages = []
        for item in result.new_items:
            if hasattr(item, "to_input_item"):
                messages.append(item.to_input_item())
            elif isinstance(item, dict):
                messages.append(item)
        return messages
    if hasattr(result, "messages"):
        return list(result.messages)
    if isinstance(result, (list, dict)):
        return [result] if isinstance(result, dict) else list(result)
    return []


def trace_from_run_result(
    result: Any,
    *,
    artifacts: list | None = None,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    task: str = "",
    trace_id: str | None = None,
) -> Trace:
    trace = from_openai_agents(
        _messages_from_result(result),
        artifacts=artifacts or [],
        task=task,
        trace_id=trace_id,
    )
    if artifacts is None:
        trace.artifacts = artifacts_for_trace(trace, baseline=baseline, git_repo=git_repo)
    return trace


def verify_openai_result(
    guard: RuntimeGuard,
    result: Any,
    *,
    artifacts: list | None = None,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    task: str = "",
    trace_id: str | None = None,
) -> AssayRunResult:
    trace = trace_from_run_result(
        result,
        artifacts=artifacts,
        baseline=baseline,
        git_repo=git_repo,
        task=task,
        trace_id=trace_id,
    )
    return guard.verify(trace)


def run_with_verification(
    guard: RuntimeGuard,
    agent: Any,
    input: Any,
    *,
    runner: Any = None,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    artifacts: list | None = None,
    **run_kwargs: Any,
) -> Any:
    if runner is None:
        try:
            from agents import Runner
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "install openai-agents or pass runner= (for example agents.Runner)"
            ) from exc
        runner = Runner
    result = runner.run_sync(agent, input, **run_kwargs)
    verify_openai_result(
        guard,
        result,
        baseline=baseline,
        git_repo=git_repo,
        artifacts=artifacts,
    )
    return result


async def run_with_verification_async(
    guard: RuntimeGuard,
    agent: Any,
    input: Any,
    *,
    runner: Any = None,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    artifacts: list | None = None,
    **run_kwargs: Any,
) -> Any:
    if runner is None:
        try:
            from agents import Runner
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "install openai-agents or pass runner= (for example agents.Runner)"
            ) from exc
        runner = Runner
    result = await runner.run(agent, input, **run_kwargs)
    verify_openai_result(
        guard,
        result,
        baseline=baseline,
        git_repo=git_repo,
        artifacts=artifacts,
    )
    return result
