"""Shared helpers for runtime integrations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters.messages import artifacts_from_git
from ..model import Artifact, Trace
from ..replay import artifacts_with_fallback, replay_tool_calls


def artifacts_for_trace(
    trace: Trace,
    *,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
) -> list[Artifact]:
    if git_repo:
        return artifacts_from_git(git_repo)
    if baseline:
        tool_calls = [(step.tool, step.args) for step in trace.steps]
        replayed = replay_tool_calls(tool_calls, baseline)
        return artifacts_with_fallback(tool_calls, baseline, replayed)
    return []
