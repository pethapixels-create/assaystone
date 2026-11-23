"""Langfuse trace/observation export importer.

Accepts a traces list (``{"data": [...]}`` or a list), a single trace with
``observations``, or a flat observation list grouped by ``traceId``. Spans whose
input looks like a file/tool call are replayed to recover artifacts.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from ..jsonl import read_jsonl
from ..model import Trace
from .common import ToolRecord, as_args, extract_text, stringify, trace_from_records

_OBSERVATION_TYPES = {"SPAN", "GENERATION", "EVENT"}


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


def _extract_traces(data: Any, default_id: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if isinstance(data, dict) and "traces" in data:
        data = data["traces"]
    if isinstance(data, dict):
        if "observations" in data or ("id" in data and ("input" in data or "output" in data)):
            return [data]
        return []
    if not isinstance(data, list) or not data:
        return []

    dict_items = [item for item in data if isinstance(item, dict)]
    if any("observations" in item for item in dict_items):
        return dict_items
    if any("traceId" in item for item in dict_items):
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in dict_items:
            groups.setdefault(str(item.get("traceId") or default_id), []).append(item)
        return [{"id": trace_id, "observations": obs} for trace_id, obs in groups.items()]
    if all(
        str(item.get("type") or "").upper() in _OBSERVATION_TYPES or "input" in item
        for item in dict_items
    ):
        return [{"id": default_id, "observations": dict_items}]
    return []


def _looks_like_tool(name: str, observation_type: str, inputs: Any) -> bool:
    if observation_type == "GENERATION":
        return False
    if not isinstance(inputs, dict):
        return False
    if any(
        key in inputs
        for key in ("file_path", "path", "command", "old_string", "new_string", "content", "cmd")
    ):
        return True
    name_lower = name.lower()
    return any(
        token in name_lower for token in ("edit", "write", "bash", "shell", "read", "test", "tool")
    )


def load_langfuse(
    path: str | Path,
    *,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    workspace: bool = False,
) -> list[Trace]:
    path = Path(path)
    data = _read_export(path)
    traces: list[Trace] = []
    for trace_data in _extract_traces(data, path.stem):
        observations = trace_data.get("observations") or trace_data.get("spans") or []
        observations.sort(
            key=lambda obs: str(obs.get("startTime") or obs.get("start_time") or "")
        )
        records: list[ToolRecord] = []
        final_message = extract_text(trace_data.get("output"))
        for observation in observations:
            observation_type = str(observation.get("type") or "").upper()
            name = str(observation.get("name") or observation_type or "observation")
            inputs = observation.get("input")
            outputs = observation.get("output")
            if observation_type == "GENERATION":
                if not final_message:
                    final_message = extract_text(outputs)
                continue
            if _looks_like_tool(name, observation_type, inputs):
                records.append(
                    ToolRecord(
                        name=name,
                        args=as_args(inputs),
                        result=stringify(outputs),
                        ok=str(observation.get("level") or "").upper() != "ERROR",
                    )
                )
        if not final_message and observations:
            final_message = extract_text(observations[-1].get("output"))
        traces.append(
            trace_from_records(
                records,
                trace_id=str(trace_data.get("id") or path.stem),
                agent="langfuse",
                task=extract_text(trace_data.get("input")),
                final_message=final_message,
                baseline=baseline,
                git_repo=git_repo,
                workspace=workspace,
            )
        )
    return traces
