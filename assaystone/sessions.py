"""Discover the latest local coding-agent transcript for a workspace."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SUPPORTED_SESSION_AGENTS = ("claude-code", "codex")


class SessionDiscoveryError(LookupError):
    """No matching local transcript could be found."""


@dataclass(frozen=True)
class SessionSource:
    path: Path
    cwd: Path | None
    agent: str


def _record_cwd(path: Path) -> Path | None:
    """Read only the transcript header needed to identify its workspace."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for _ in range(40):
                line = handle.readline()
                if not line:
                    break
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                payload = record.get("payload")
                raw = payload.get("cwd") if isinstance(payload, dict) else None
                if not raw:
                    raw = record.get("cwd")
                if raw:
                    try:
                        return Path(str(raw)).expanduser().resolve()
                    except OSError:
                        return Path(str(raw)).expanduser()
    except OSError:
        return None
    return None


def _candidate_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    try:
        files = [path for path in root.rglob("*.jsonl") if path.is_file()]
    except OSError:
        return ()
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def _workspace_match(session_cwd: Path, requested: Path) -> bool:
    if session_cwd == requested:
        return True
    try:
        requested.relative_to(session_cwd)
        return True
    except ValueError:
        return False


def session_root(agent: str, root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root).expanduser().resolve()
    if agent == "codex":
        return Path(
            os.environ.get("ASSAYSTONE_CODEX_ROOT", "~/.codex/sessions")
        ).expanduser().resolve()
    if agent == "claude-code":
        return Path(
            os.environ.get("ASSAYSTONE_CLAUDE_ROOT", "~/.claude/projects")
        ).expanduser().resolve()
    raise ValueError(f"unknown session agent: {agent}")


def find_latest_session(
    agent: str,
    *,
    cwd: str | Path = ".",
    root: str | Path | None = None,
) -> SessionSource:
    """Return the newest transcript whose recorded workspace contains ``cwd``."""
    if agent not in SUPPORTED_SESSION_AGENTS:
        raise ValueError(f"unknown session agent: {agent}")
    requested = Path(cwd).expanduser().resolve()
    search_root = session_root(agent, root)
    for path in _candidate_files(search_root):
        recorded = _record_cwd(path)
        if recorded is not None and _workspace_match(recorded, requested):
            return SessionSource(path=path.resolve(), cwd=recorded, agent=agent)
    raise SessionDiscoveryError(
        f"no recent {agent} transcript found for {requested} under {search_root}"
    )
