"""Isolated workspace: a fresh copy of the baseline plus the agent's artifacts."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

from .model import Artifact

_IGNORE = shutil.ignore_patterns(
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "*.pyc",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    "target",
    "vendor",
    ".next",
    ".nuxt",
    "coverage",
)


class Workspace:
    def __init__(self, baseline: str | Path):
        self.baseline = Path(baseline).resolve()
        if self.baseline in {Path.home().resolve(), Path("/")}:
            raise ValueError(
                "refusing to copy the home directory or filesystem root as a workspace; "
                "point --baseline at the project root"
            )
        self._tmp = tempfile.TemporaryDirectory(prefix="assaystone-")
        self.root = Path(self._tmp.name) / "repo"
        shutil.copytree(self.baseline, self.root, ignore=_IGNORE)
        self.changed: list[tuple[str, str]] = []

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._tmp.cleanup()

    def _safe(self, rel: str) -> Path:
        rel = rel.replace("\\", "/")
        parts = Path(rel).parts
        if not rel or rel.startswith("/") or ".." in parts:
            raise ValueError(f"unsafe artifact path: {rel!r}")
        target = (self.root / rel).resolve()
        if not target.is_relative_to(self.root.resolve()):
            raise ValueError(f"artifact escapes workspace: {rel!r}")
        return target

    def apply(self, artifacts: Iterable[Artifact]) -> None:
        for artifact in artifacts:
            target = self._safe(artifact.path)
            if artifact.change == "deleted":
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(artifact.content, encoding="utf-8")
            self.changed.append((artifact.path, artifact.change))

    def read(self, rel: str) -> str:
        return self._safe(rel).read_text(encoding="utf-8")

    def exists(self, rel: str) -> bool:
        return self._safe(rel).exists()

    def run(self, command: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable if part == "{python}" else part for part in command]
        env = os.environ.copy()
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(self.root) + (os.pathsep + existing if existing else "")
        return subprocess.run(
            cmd,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
