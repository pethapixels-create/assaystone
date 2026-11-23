"""Replay tool calls to recover artifacts and infer test evidence.

Shared by the message/transcript audit and by the LangSmith / Langfuse importers.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .model import Artifact, Trace

_EDIT_TOOLS = {
    "write",
    "write_file",
    "create_file",
    "create",
    "edit",
    "str_replace",
    "replace_in_file",
    "str_replace_editor",
    "multiedit",
    "delete_file",
    "remove_file",
}


def relative_path(raw: Any, baseline: Path) -> str | None:
    if not raw:
        return None
    path = Path(str(raw))
    try:
        if path.is_absolute():
            return path.resolve().relative_to(baseline).as_posix()
        text = path.as_posix()
        if text == ".." or text.startswith("../"):
            return None
        return text
    except (ValueError, OSError):
        return None


def replay_tool_calls(
    tool_calls: Iterable[tuple[str, dict[str, Any]]],
    baseline: str | Path,
) -> list[Artifact]:
    """Apply Write/Edit/MultiEdit tool calls to the baseline and return the diff."""
    root = Path(baseline).resolve()
    current: dict[str, str | None] = {}

    def load(relative: str) -> str | None:
        if relative not in current:
            path = root / relative
            try:
                current[relative] = path.read_text(encoding="utf-8") if path.exists() else None
            except (UnicodeDecodeError, OSError):
                current[relative] = None
        return current[relative]

    for name, args in tool_calls:
        tool = name.lower()
        raw_path = args.get("file_path") or args.get("path") or args.get("file")
        relative = relative_path(raw_path, root)
        if relative is None:
            continue
        if tool in {"write", "write_file", "create_file", "create"}:
            content = args.get("content")
            if content is not None:
                current[relative] = str(content)
        elif tool in {"edit", "str_replace", "replace_in_file", "str_replace_editor"}:
            old = args.get("old_string", args.get("old_str", args.get("old")))
            new = args.get("new_string", args.get("new_str", args.get("new", "")))
            if old is None:
                continue
            text = load(relative)
            if text is None:
                continue
            current[relative] = text.replace(
                str(old),
                str(new or ""),
                -1 if args.get("replace_all") else 1,
            )
        elif tool == "multiedit":
            text = load(relative)
            if text is None:
                continue
            for edit in args.get("edits", []) or []:
                old = edit.get("old_string", edit.get("old_str"))
                new = edit.get("new_string", edit.get("new_str", ""))
                if old is not None:
                    text = text.replace(str(old), str(new or ""), 1)
            current[relative] = text
        elif tool in {"delete_file", "remove_file"}:
            current[relative] = None

    artifacts: list[Artifact] = []
    for relative, content in sorted(current.items()):
        path = root / relative
        base_text: str | None = None
        if path.exists():
            try:
                base_text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
        if content is None:
            if base_text is not None:
                artifacts.append(Artifact(relative, "", "deleted"))
        elif base_text is None:
            artifacts.append(Artifact(relative, content, "added"))
        elif content != base_text:
            artifacts.append(Artifact(relative, content, "modified"))
    return artifacts


def touched_paths(
    tool_calls: Iterable[tuple[str, dict[str, Any]]],
    baseline: str | Path,
) -> set[str]:
    root = Path(baseline).resolve()
    paths: set[str] = set()
    for name, args in tool_calls:
        if name.lower() not in _EDIT_TOOLS:
            continue
        raw = args.get("file_path") or args.get("path") or args.get("file")
        relative = relative_path(raw, root)
        if relative:
            paths.add(relative)
    return paths


def workspace_artifacts(
    tool_calls: Iterable[tuple[str, dict[str, Any]]],
    baseline: str | Path,
) -> list[Artifact]:
    """Collect current files touched by edit tools (post-session / hook mode).

    The baseline is the workspace *after* the session, so replaying old_string
    replacements would fail. We only need the changed paths and their current
    contents for path rules, syntax checks, and debug-print scans.
    """
    root = Path(baseline).resolve()
    artifacts: list[Artifact] = []
    for relative in sorted(touched_paths(tool_calls, baseline)):
        path = root / relative
        try:
            if path.is_file():
                artifacts.append(Artifact(relative, path.read_text(encoding="utf-8"), "modified"))
            else:
                artifacts.append(Artifact(relative, "", "deleted"))
        except (UnicodeDecodeError, OSError):
            continue
    return artifacts


def artifacts_with_fallback(
    tool_calls: list[tuple[str, dict[str, Any]]],
    baseline: str | Path,
    replayed: list[Artifact],
) -> list[Artifact]:
    """Use workspace artifacts when replay does not cover every touched path.

    A partial replay means the baseline is the post-session workspace, not the
    pre-session state. In that case the current file contents are the truth.
    """
    touched = touched_paths(tool_calls, baseline)
    replayed_paths = {artifact.path for artifact in replayed}
    if touched and not touched <= replayed_paths:
        return workspace_artifacts(tool_calls, baseline)
    return replayed


_TEST_RUNNER = re.compile(
    r"(?:^|[;&|]\s*)(?:"
    r"pytest|"
    r"python(?:[0-9.]+)?\s+-m\s+(?:pytest|unittest)|"
    r"npm\s+(?:run\s+)?test|"
    r"pnpm\s+test|"
    r"yarn\s+test|"
    r"npx\s+(?:jest|vitest)|"
    r"go\s+test|"
    r"cargo\s+test|"
    r"mvn\s+[^;&|]*\btest\b|"
    r"(?:\./)?mvnw\s+[^;&|]*\btest\b|"
    r"gradle\s+[^;&|]*\btest\b|"
    r"(?:\./)?gradlew\s+[^;&|]*\btest\b|"
    r"jest|"
    r"vitest|"
    r"rspec|"
    r"dotnet\s+test|"
    r"ctest"
    r")\b",
    re.IGNORECASE,
)


def _repo_root(repo: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def is_git_repo(repo: str | Path) -> bool:
    root = _repo_root(Path(repo).resolve())
    if root is None:
        return False
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def is_git_root(repo: str | Path) -> bool:
    root = Path(repo).resolve()
    return _repo_root(root) == root


def git_preimage(repo: str | Path, paths: Iterable[str]) -> tempfile.TemporaryDirectory:
    """Create a temporary pre-session baseline from HEAD for the given paths."""
    root = Path(repo).resolve()
    repo_root = _repo_root(root)
    temporary = tempfile.TemporaryDirectory(prefix="assaystone-preimage-")
    target_root = Path(temporary.name)
    if repo_root is None:
        return temporary
    for relative in sorted({str(path) for path in paths}):
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            continue
        absolute = (root / relative).resolve()
        try:
            repository_path = absolute.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        result = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"HEAD:{repository_path}"],
            capture_output=True,
            text=True,
            errors="replace",
        )
        if result.returncode != 0:
            continue
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.stdout, encoding="utf-8")
    return temporary


def _result_text(value: Any) -> str:
    text = str(value or "")
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return text
        if isinstance(data, dict):
            for key in ("output", "result", "text", "content"):
                if key in data:
                    inner = data[key]
                    if isinstance(inner, (dict, list)):
                        return json.dumps(inner, ensure_ascii=False)
                    return str(inner)
    return text


def _test_outcome(output: str, ok: bool) -> int | None:
    if not ok:
        return 1
    text = output.lower()
    if "build failure" in text or "build failed" in text:
        return 1
    if re.search(r"failures?=\s*[1-9]\d*", text):
        return 1
    if re.search(r"\b[1-9]\d*\s+(?:failed|failure|failures|errors?)\b", text):
        return 1
    if re.search(r"(?:^|\n)\s*failed\b", text) or "traceback" in text:
        return 1
    zero = re.search(r"\b0\s+(?:failed|failures?|errors?)\b", text) or "no failures" in text
    passed = re.search(r"\b[1-9]\d*\s+passed\b", text)
    success = (
        zero
        or passed
        or re.search(r"(?:^|\n)\s*ok\b", text)
        or "build success" in text
        or "tests passed" in text
        or "all tests passed" in text
        or "test run successful" in text
    )
    return 0 if success else None


def infer_test_evidence(trace: Trace) -> None:
    """Infer test_exit_code from the last test-runner step, or leave it unset."""
    code: int | None = None
    for step in trace.steps:
        tool = step.tool.lower()
        if tool not in {"bash", "shell", "run_tests", "execute_command", "terminal"}:
            continue
        command = str(step.args.get("command") or step.args.get("cmd") or "")
        if not _TEST_RUNNER.search(command):
            continue
        outcome = _test_outcome(_result_text(step.result), step.ok)
        if outcome is not None:
            code = outcome
    if code is not None:
        trace.evidence.setdefault("test_exit_code", code)
