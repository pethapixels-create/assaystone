"""Read JSONL without Unicode line-boundary surprises.

``str.splitlines()`` also splits on U+0085, U+2028, and friends, which can appear
inside a valid JSON string and silently break a line. JSONL is newline-delimited,
so read on ``\\n`` only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: str | Path, *, skip_invalid: bool = True) -> tuple[list[Any], list[str]]:
    entries: list[Any] = []
    errors: list[str] = []
    with Path(path).open("r", encoding="utf-8", newline="\n") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.rstrip("\r\n")
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                if not skip_invalid:
                    raise
                errors.append(f"line {number}: {exc.msg}")
    return entries, errors
