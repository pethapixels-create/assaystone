"""LangSmith run export importer.

Accepts a JSON list of runs, a ``{"runs": [...]}`` object, a nested run tree with
``child_runs``, or a JSONL file. Groups runs by ``trace_id`` (or the file stem) and
replays tool runs to recover artifacts.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Iterable

from ..jsonl import read_jsonl
from ..model import Trace
from .common import ToolRecord, as_args, extract_text, stringify, trace_from_records


def _read_export(path: Path) -> Any:
    if path.suffix.lower() == ".jsonl":
        entries, errors = read_jsonl(path)
        if errors:
            warnings.warn(
                f"{path.name}: skipped {len(errors)} invalid JSONL line(s)",
                RuntimeWarning,
                stacklevel=2,
            )
        return entries
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(
    data: Any,
    inherited: str | None = None,
    default: str = "trace",
) -> Iterable[tuple[dict[str, Any], str]]:
    if isinstance(data, dict):
        runs = data.get("runs")
        if isinstance(runs, list):
            for run in runs:
                yield from _flatten(run, inherited, default)
            return
        group = str(data.get("trace_id") or inherited or data.get("id") or default)
        yield data, group
        for child in data.get("child_runs") or []:
            yield from _flatten(child, group, default)
    elif isinstance(data, list):
        for item in data:
            yield from _flatten(item, inherited, default)


def _looks_like_tool(run_type: str, name: str, inputs: Any) -> bool:
    if run_type in ("tool", "function"):
        return True
    if run_type in ("llm", "chat_model", "prompt"):
        return False
    if not isinstance(inputs, dict):
        return False
    if any(
        key in inputs
        for key in ("file_path", "path", "command", "old_string", "new_string", "content", "cmd")
    ):
        return True
    return name.lower() in {"read", "edit", "write", "bash", "shell", "run_tests"}


def _task_from_inputs(inputs: Any) -> str:
    if not isinstance(inputs, dict):
        return extract_text(inputs)[:200]
    messages = inputs.get("messages")
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or message.get("type") or "").lower()
            if role in ("user", "human"):
                text = extract_text(message.get("content") or message)
                if text:
                    return text[:200]
    for key in ("input", "prompt", "question", "messages"):
        if key in inputs:
            text = extract_text(inputs[key])
            if text:
                return text[:200]
    return extract_text(inputs)[:200]


def load_langsmith(
    path: str | Path,
    *,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    workspace: bool = False,
) -> list[Trace]:
    path = Path(path)
    data = _read_export(path)
    groups: dict[str, list[dict[str, Any]]] = {}
    for run, group in _flatten(data, inherited=path.stem, default=path.stem):
        groups.setdefault(group, []).append(run)

    traces: list[Trace] = []
    for trace_id, runs in groups.items():
        runs.sort(key=lambda run: str(run.get("start_time") or run.get("startTime") or ""))
        records: list[ToolRecord] = []
        final_message = ""
        task = ""
        for run in runs:
            run_type = str(run.get("run_type") or run.get("type") or "").lower()
            name = str(run.get("name") or run.get("id") or "run")
            inputs = run.get("inputs") or run.get("input") or {}
            outputs = run.get("outputs") or run.get("output") or {}
            if run_type in ("llm", "chat_model", "prompt"):
                if not task:
                    task = _task_from_inputs(inputs)
                text = extract_text(outputs)
                if text:
                    final_message = text
                continue
            if _looks_like_tool(run_type, name, inputs):
                records.append(
                    ToolRecord(
                        name=name,
                        args=as_args(inputs),
                        result=stringify(outputs),
                        ok=not bool(run.get("error")),
                    )
                )
        if not final_message and runs:
            final_message = extract_text(runs[-1].get("outputs") or runs[-1].get("output"))
        if not task and runs:
            task = _task_from_inputs(runs[0].get("inputs") or runs[0].get("input"))
        traces.append(
            trace_from_records(
                records,
                trace_id=trace_id,
                agent="langsmith",
                task=task,
                final_message=final_message,
                baseline=baseline,
                git_repo=git_repo,
                workspace=workspace,
            )
        )
    return traces
