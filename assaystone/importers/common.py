"""Shared helpers for trace importers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..adapters.messages import artifacts_from_git
from ..model import Step, Trace
from ..replay import (
    artifacts_with_fallback,
    infer_test_evidence,
    replay_tool_calls,
    workspace_artifacts,
)


@dataclass
class ToolRecord:
    name: str
    args: dict[str, Any]
    result: str = ""
    ok: bool = True


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("output", "result", "text", "content", "message", "messages", "choices", "data"):
            if key in value:
                text = extract_text(value[key])
                if text:
                    return text
        return ""
    if isinstance(value, list):
        for item in reversed(value):
            text = extract_text(item)
            if text:
                return text
    return ""


def as_args(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    return {"value": value} if value is not None else {}


def trace_from_records(
    records: list[ToolRecord],
    *,
    trace_id: str,
    agent: str,
    task: str = "",
    final_message: str = "",
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    evidence: dict[str, Any] | None = None,
    workspace: bool = False,
) -> Trace:
    tool_calls = [(record.name, record.args) for record in records]
    artifacts = []
    if workspace and baseline:
        artifacts = workspace_artifacts(tool_calls, baseline)
    elif git_repo:
        artifacts = artifacts_from_git(git_repo)
    elif baseline:
        artifacts = replay_tool_calls(tool_calls, baseline)
        artifacts = artifacts_with_fallback(tool_calls, baseline, artifacts)
    trace = Trace(
        id=trace_id,
        task=task[:200] if task else "",
        agent=agent,
        steps=[Step(record.name, record.args, record.result, record.ok) for record in records],
        artifacts=artifacts,
        final_message=final_message,
        evidence=dict(evidence or {}),
    )
    infer_test_evidence(trace)
    return trace
