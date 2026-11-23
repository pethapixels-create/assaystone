"""Trace importers for observability tools."""
from __future__ import annotations

from typing import Any

from .langfuse import load_langfuse
from .langsmith import load_langsmith
from .otel import load_otel

__all__ = ["detect_import_format", "load_langfuse", "load_langsmith", "load_otel"]


def detect_import_format(data: Any) -> str | None:
    """Best-effort detection of a LangSmith or Langfuse export shape."""
    if isinstance(data, dict):
        if any(key in data for key in ("resourceSpans", "scopeSpans", "spans")):
            return "otel"
        if "runs" in data or "run_type" in data or "child_runs" in data:
            return "langsmith"
        if "observations" in data:
            return "langfuse"
        if "data" in data:
            inner = data["data"]
            if isinstance(inner, list) and inner:
                first = inner[0]
                if isinstance(first, dict):
                    if "run_type" in first or "trace_id" in first or "child_runs" in first:
                        return "langsmith"
                    if "observations" in first or "traceId" in first:
                        return "langfuse"
                    if str(first.get("type") or "").upper() in {"SPAN", "GENERATION", "EVENT"}:
                        return "langfuse"
        return None
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            if "traceId" in first and ("spanId" in first or "startTimeUnixNano" in first):
                return "otel"
            if "run_type" in first or "trace_id" in first or "child_runs" in first:
                return "langsmith"
            if "observations" in first or "traceId" in first:
                return "langfuse"
            if str(first.get("type") or "").upper() in {"SPAN", "GENERATION", "EVENT"}:
                return "langfuse"
    return None
