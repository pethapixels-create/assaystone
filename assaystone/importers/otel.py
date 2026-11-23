"""OpenTelemetry GenAI span importer (OTLP JSON).

Accepts ``{"resourceSpans": [...]}``, ``{"scopeSpans": [...]}``, ``{"spans": [...]}``,
or a flat list of spans. Tool spans are detected from ``gen_ai.operation.name`` /
``gen_ai.tool.name`` and replayed to recover artifacts.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from ..jsonl import read_jsonl
from ..model import Trace
from .common import ToolRecord, as_args, extract_text, stringify, trace_from_records

_TOOL_OPS = {"execute_tool", "tool", "tool_call", "invoke_tool"}


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


def _value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    for key in ("stringValue", "intValue", "doubleValue", "boolValue", "bytesValue"):
        if key in value:
            raw = value[key]
            if key == "intValue":
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    return raw
            if key == "doubleValue":
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return raw
            if key == "boolValue":
                return bool(raw)
            return raw
    if "arrayValue" in value:
        return [
            _value(item)
            for item in (value["arrayValue"] or {}).get("values", [])
        ]
    if "kvlistValue" in value:
        return {
            item.get("key"): _value(item.get("value") or {})
            for item in (value["kvlistValue"] or {}).get("values", [])
            if isinstance(item, dict)
        }
    return None


def _attrs(span: dict[str, Any]) -> dict[str, Any]:
    attributes = span.get("attributes") or []
    return {
        attribute.get("key"): _value(attribute.get("value") or {})
        for attribute in attributes
        if isinstance(attribute, dict) and attribute.get("key")
    }


def _spans(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        if "resourceSpans" in data:
            spans: list[dict[str, Any]] = []
            for resource in data["resourceSpans"] or []:
                for scope in resource.get("scopeSpans") or []:
                    spans.extend(scope.get("spans") or [])
            return spans
        if "scopeSpans" in data:
            spans = []
            for scope in data["scopeSpans"] or []:
                spans.extend(scope.get("spans") or [])
            return spans
        if "spans" in data:
            return list(data["spans"] or [])
    if isinstance(data, list):
        return [span for span in data if isinstance(span, dict)]
    return []


def _status_ok(span: dict[str, Any]) -> bool:
    status = span.get("status") or {}
    code = status.get("code")
    if isinstance(code, str):
        return code.upper() not in ("ERROR", "2")
    return code != 2


def _is_tool(span: dict[str, Any], attrs: dict[str, Any]) -> bool:
    operation = str(attrs.get("gen_ai.operation.name") or "").lower()
    if operation in _TOOL_OPS:
        return True
    if attrs.get("gen_ai.tool.name"):
        return True
    name = str(span.get("name") or "").lower()
    return "execute_tool" in name and bool(attrs.get("gen_ai.tool.call.arguments"))


def _text_attr(attrs: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key in attrs:
            text = extract_text(attrs[key])
            if text:
                return text
    return ""


def load_otel(
    path: str | Path,
    *,
    baseline: str | Path | None = None,
    git_repo: str | Path | None = None,
    workspace: bool = False,
) -> list[Trace]:
    path = Path(path)
    spans = _spans(_read_export(path))
    groups: dict[str, list[dict[str, Any]]] = {}
    for span in spans:
        groups.setdefault(str(span.get("traceId") or path.stem), []).append(span)

    traces: list[Trace] = []
    for trace_id, trace_spans in groups.items():
        trace_spans.sort(key=lambda span: str(span.get("startTimeUnixNano") or ""))
        records: list[ToolRecord] = []
        final_message = ""
        task = ""
        for span in trace_spans:
            attrs = _attrs(span)
            if _is_tool(span, attrs):
                name = str(
                    attrs.get("gen_ai.tool.name")
                    or span.get("name")
                    or "tool"
                )
                raw_args = (
                    attrs.get("gen_ai.tool.call.arguments")
                    or attrs.get("tool.arguments")
                    or attrs.get("input")
                )
                raw_result = (
                    attrs.get("gen_ai.tool.call.result")
                    or attrs.get("tool.result")
                    or attrs.get("output")
                )
                records.append(
                    ToolRecord(
                        name=name,
                        args=as_args(raw_args),
                        result=stringify(raw_result),
                        ok=_status_ok(span),
                    )
                )
                continue
            output = _text_attr(
                attrs,
                "gen_ai.output.messages",
                "gen_ai.response.text",
                "gen_ai.completion",
            )
            if output:
                final_message = output
            if not task:
                task = _text_attr(
                    attrs,
                    "gen_ai.input.messages",
                    "gen_ai.prompt",
                )
        traces.append(
            trace_from_records(
                records,
                trace_id=trace_id,
                agent="otel",
                task=task,
                final_message=final_message,
                baseline=baseline,
                git_repo=git_repo,
                workspace=workspace,
            )
        )
    return traces
