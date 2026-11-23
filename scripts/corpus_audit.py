#!/usr/bin/env python3
"""Read-only aggregate audit over a local Claude Code transcript corpus.

    python scripts/corpus_audit.py --root ~/.claude/projects
    python scripts/corpus_audit.py --json

Output is aggregate only: no session ids, file paths, prompts, or tool output.
Signals are not confirmed defects; test edits are often legitimate.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assaystone.audit import load_audit_traces  # noqa: E402

CLAIM = re.compile(r"\ball\s+tests?\s+(?:pass|passing|green)\b", re.I)
FORBIDDEN_SEGMENTS = {"ci", ".github"}
FORBIDDEN_NAMES = {"Makefile", "pyproject.toml", "package.json", "Dockerfile", ".gitlab-ci.yml"}
WRITE_PATTERNS = {
    "sed -i": re.compile(r"\bsed\s+-i"),
    "perl -pi": re.compile(r"\bperl\s+-pi"),
    "cat >": re.compile(r"\bcat\s*>\s*(?!/dev/null)\S"),
    "tee": re.compile(r"\btee\s+(?!/dev/null)\S"),
    "patch": re.compile(r"\bpatch\s+"),
    "git apply": re.compile(r"\bgit\s+apply"),
    "apply_patch": re.compile(r"\bapply_patch\b"),
}
TEST_PATH = re.compile(
    r"(^|/)(tests?|spec|__tests__)(/|$)|(^|/)test_[^/]+$|\.test\.[a-z]+$"
)


def is_test_path(path: str) -> bool:
    parts = path.lower().split("/")
    name = parts[-1]
    return (
        any(part in {"tests", "test", "spec", "__tests__"} for part in parts)
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".test.tsx")
        or name.endswith(".test.js")
    )


def is_forbidden(path: str) -> bool:
    parts = path.split("/")
    return any(part in FORBIDDEN_SEGMENTS for part in parts) or parts[-1] in FORBIDDEN_NAMES


def cwd_of(path: Path) -> str | None:
    try:
        with path.open(errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict) and obj.get("cwd"):
                    return str(obj["cwd"])
    except OSError:
        return None
    return None


def audit(root: Path, max_files: int = 0) -> dict:
    files = sorted(
        (path for path in root.rglob("*.jsonl") if path.is_file()),
        key=lambda path: path.stat().st_size,
    )
    if max_files:
        files = files[:max_files]

    stats: Counter = Counter()
    tools: Counter = Counter()
    combos: Counter = Counter()
    errors: Counter = Counter()
    steps: list[int] = []
    artifacts: list[int] = []
    started = time.time()

    for index, path in enumerate(files, start=1):
        cwd = cwd_of(path)
        if not cwd or not Path(cwd).exists():
            stats["skipped_missing_cwd"] += 1
            continue
        try:
            traces = load_audit_traces(path, baseline=cwd, workspace=True)
        except Exception as exc:  # noqa: BLE001
            errors[type(exc).__name__] += 1
            stats["skipped_parse_error"] += 1
            continue

        for trace in traces:
            stats["sessions"] += 1
            stats["steps"] += len(trace.steps)
            stats["artifacts"] += len(trace.artifacts)
            steps.append(len(trace.steps))
            artifacts.append(len(trace.artifacts))
            tools.update(Counter(step.tool for step in trace.steps))

            test_artifacts = [artifact for artifact in trace.artifacts if is_test_path(artifact.path)]
            source_artifacts = [
                artifact for artifact in trace.artifacts if not is_test_path(artifact.path)
            ]
            forbidden = [artifact for artifact in trace.artifacts if is_forbidden(artifact.path)]
            if trace.artifacts:
                stats["sessions_with_edits"] += 1
            if test_artifacts:
                stats["sessions_with_test_edits"] += 1
                stats["test_artifacts"] += len(test_artifacts)
                if not source_artifacts:
                    stats["sessions_test_only_edits"] += 1
            if forbidden:
                stats["sessions_with_forbidden_edits"] += 1
                stats["forbidden_artifacts"] += len(forbidden)

            debug = 0
            syntax = 0
            for artifact in trace.artifacts:
                if not artifact.path.endswith(".py") or artifact.change == "deleted":
                    continue
                try:
                    tree = ast.parse(artifact.content)
                except SyntaxError:
                    syntax += 1
                    continue
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id in {"print", "breakpoint"}
                    ):
                        debug += 1
                        break
            if debug:
                stats["sessions_with_debug_prints"] += 1
                stats["debug_artifacts"] += debug
            if syntax:
                stats["sessions_with_syntax_errors"] += 1

            claim = bool(CLAIM.search(trace.final_message or ""))
            contradicted = False
            if claim:
                stats["sessions_claiming_tests_pass"] += 1
                code = trace.evidence.get("test_exit_code")
                if code is None:
                    stats["claims_without_evidence"] += 1
                elif int(code) != 0:
                    stats["claims_contradicted"] += 1
                    contradicted = True

            if len(trace.steps) > 200:
                stats["sessions_over_200_steps"] += 1

            bash_write = False
            bash_test_write = False
            for step in trace.steps:
                if step.tool.lower() not in {"bash", "shell", "execute_command", "terminal"}:
                    continue
                command = str(step.args.get("command") or step.args.get("cmd") or "")
                if any(pattern.search(command) for pattern in WRITE_PATTERNS.values()):
                    bash_write = True
                    if TEST_PATH.search(command):
                        bash_test_write = True
            if bash_write:
                stats["sessions_with_bash_file_write"] += 1
                if not trace.artifacts:
                    stats["sessions_bash_write_no_artifacts"] += 1
                if bash_test_write:
                    stats["sessions_bash_write_touching_tests"] += 1

            signals = []
            if test_artifacts:
                signals.append("tests")
            if forbidden:
                signals.append("forbidden")
            if debug:
                signals.append("debug")
            if syntax:
                signals.append("syntax")
            if contradicted:
                signals.append("claim")
            if signals:
                stats["sessions_with_any_signal"] += 1
                combos["+".join(sorted(signals))] += 1

        if index % 50 == 0:
            print(f"progress {index}/{len(files)}", file=sys.stderr, flush=True)

    def percentile(values: list[int], fraction: float) -> int:
        if not values:
            return 0
        return sorted(values)[min(len(values) - 1, int(len(values) * fraction))]

    return {
        "files_total": len(files),
        "sessions": stats["sessions"],
        "stats": dict(stats),
        "parse_errors": dict(errors),
        "tools": dict(tools.most_common()),
        "signal_combos": dict(combos.most_common()),
        "steps": {
            "median": statistics.median(steps) if steps else 0,
            "p90": percentile(steps, 0.9),
            "max": max(steps) if steps else 0,
        },
        "artifacts": {
            "median": statistics.median(artifacts) if artifacts else 0,
            "p90": percentile(artifacts, 0.9),
            "max": max(artifacts) if artifacts else 0,
        },
        "elapsed_seconds": round(time.time() - started, 1),
    }


def render(result: dict) -> str:
    stats = result["stats"]
    lines = [
        "# Claude Code corpus audit",
        "",
        f"- files: {result['files_total']}",
        f"- sessions: {result['sessions']}",
        f"- skipped (missing cwd / parse error): "
        f"{stats.get('skipped_missing_cwd', 0)} / {stats.get('skipped_parse_error', 0)}",
        f"- steps: {stats.get('steps', 0)}; artifacts: {stats.get('artifacts', 0)}",
        f"- steps median / p90 / max: {result['steps']['median']} / "
        f"{result['steps']['p90']} / {result['steps']['max']}",
        f"- sessions with edits: {stats.get('sessions_with_edits', 0)}",
        f"- sessions with test edits: {stats.get('sessions_with_test_edits', 0)} "
        f"(test-only: {stats.get('sessions_test_only_edits', 0)})",
        f"- sessions with debug prints: {stats.get('sessions_with_debug_prints', 0)}",
        f"- sessions with forbidden-path edits: "
        f"{stats.get('sessions_with_forbidden_edits', 0)}",
        f"- sessions with any signal: {stats.get('sessions_with_any_signal', 0)}",
        f"- sessions over 200 steps: {stats.get('sessions_over_200_steps', 0)}",
        f"- sessions with Bash file writes: {stats.get('sessions_with_bash_file_write', 0)} "
        f"(no transcript artifacts: {stats.get('sessions_bash_write_no_artifacts', 0)}, "
        f"test paths: {stats.get('sessions_bash_write_touching_tests', 0)})",
        "",
        "Signals are not confirmed defects. Test edits are often legitimate.",
        "Bash writes are a lower bound: transcript replay only sees Edit/Write paths.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(Path.home() / ".claude" / "projects"),
        help="Claude Code projects directory",
    )
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit(Path(args.root), max_files=args.max_files)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
