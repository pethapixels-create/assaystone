"""Audit existing agent traces for silent failures.

The audit is the acquisition path: it does not require a contract. It loads a
trace, transcript, or message list, reconstructs the changed files, runs a default
rule set, and reports findings plus a suggested contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .adapters.messages import artifacts_from_git, from_messages
from .contract import Contract
from .importers import detect_import_format, load_langfuse, load_langsmith, load_otel
from .init import build_contract
from .model import ESCALATE, FAIL, Artifact, Trace
from .replay import (
    artifacts_with_fallback,
    infer_test_evidence,
    replay_tool_calls,
    workspace_artifacts,
)
from .runner import run_contract

SEVERITY: dict[str, str] = {
    "diff.syntax": "critical",
    "ops.json_valid": "critical",
    "ops.amount_conserved": "critical",
    "tests.integrity": "high",
    "diff.forbidden_paths": "high",
    "evidence.claims": "high",
    "ops.no_double_refund": "high",
    "ops.refund_limit": "high",
    "ops.status_consistent": "high",
    "ops.approval_recorded": "high",
    "tests.pass": "high",
    "diff.public_api": "medium",
    "quality.no_debug_prints": "medium",
    "diff.max_lines": "low",
    "budget.steps": "low",
}
_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


class AuditError(Exception):
    """The input could not be audited."""


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _blocks(content: Any) -> list[Any]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return content
    if content is None:
        return []
    return [content]


def _block_type(block: Any) -> str:
    explicit = _get(block, "type")
    if explicit:
        return str(explicit)
    return type(block).__name__.lower()


def _looks_like_claude_code(entries: Sequence[Any]) -> bool:
    return any(
        isinstance(entry, dict)
        and entry.get("type") in ("user", "assistant")
        and "message" in entry
        for entry in entries
    )


def _normalize_claude_code(entries: Sequence[Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        message_type = entry.get("type")
        if message_type not in ("user", "assistant"):
            continue
        message = entry.get("message") or {}
        content = message.get("content")
        if content is None and "content" in entry:
            content = entry["content"]
        messages.append({"type": message_type, "content": content})
    return messages


def _tool_uses(messages: Sequence[Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for message in messages:
        message_type = str(_get(message, "type") or _get(message, "role") or "").lower()
        if message_type not in ("assistant", "ai", "model"):
            continue
        for block in _blocks(_get(message, "content")):
            if _block_type(block) == "tool_use":
                name = str(_get(block, "name") or "")
                raw_args = _get(block, "input") or {}
                yield name, dict(raw_args) if isinstance(raw_args, dict) else {}


def reconstruct_artifacts(messages: Sequence[Any], baseline: str | Path) -> list[Artifact]:
    """Replay Write/Edit/MultiEdit tool calls on the baseline to recover artifacts."""
    return replay_tool_calls(_tool_uses(messages), baseline)


def _trace_from_messages(
    messages: Sequence[Any],
    *,
    source: Path,
    agent: str,
    trace_id: str | None,
    git_repo: str | Path | None,
    baseline: str | Path | None,
    workspace: bool = False,
) -> Trace:
    artifacts: list[Artifact] = []
    if workspace and baseline:
        artifacts = workspace_artifacts(_tool_uses(messages), baseline)
    elif git_repo:
        artifacts = artifacts_from_git(git_repo)
    elif baseline:
        tool_calls = list(_tool_uses(messages))
        artifacts = replay_tool_calls(tool_calls, baseline)
        artifacts = artifacts_with_fallback(tool_calls, baseline, artifacts)
    trace = from_messages(
        messages,
        artifacts=artifacts,
        agent=agent,
        trace_id=trace_id or source.stem,
    )
    if not trace.task:
        trace.task = trace.input.splitlines()[0][:200] if trace.input else ""
    infer_test_evidence(trace)
    return trace


def _read_jsonl(path: Path) -> list[Any]:
    entries: list[Any] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise AuditError(f"{path}:{number}: invalid JSON ({exc})") from exc
    return entries


def _session_id(entries: Sequence[Any]) -> str | None:
    for entry in entries:
        if isinstance(entry, dict) and entry.get("sessionId"):
            return str(entry["sessionId"])
    return None


def _messages_session_id(messages: Sequence[Any]) -> str | None:
    for message in messages:
        if not isinstance(message, dict):
            continue
        session = message.get("sessionId") or message.get("session_id")
        if session:
            return str(session)
        if str(message.get("type") or "").lower() == "result":
            session = message.get("session_id") or message.get("sessionId")
            if session:
                return str(session)
    return None


def _load_import(
    path: Path,
    format: str,
    *,
    git_repo: str | Path | None,
    baseline: str | Path | None,
    workspace: bool,
) -> list[Trace]:
    if format == "langsmith":
        return load_langsmith(path, baseline=baseline, git_repo=git_repo, workspace=workspace)
    if format == "langfuse":
        return load_langfuse(path, baseline=baseline, git_repo=git_repo, workspace=workspace)
    return load_otel(path, baseline=baseline, git_repo=git_repo, workspace=workspace)


def _load_file(
    path: Path,
    *,
    format: str,
    git_repo: str | Path | None,
    baseline: str | Path | None,
    workspace: bool,
) -> list[Trace]:
    suffix = path.suffix.lower()
    if suffix not in (".json", ".jsonl"):
        raise AuditError(f"unsupported file type: {path}")

    if format in ("langsmith", "langfuse", "otel"):
        return _load_import(path, format, git_repo=git_repo, baseline=baseline, workspace=workspace)

    if suffix == ".jsonl":
        entries = _read_jsonl(path)
        if format == "trace":
            raise AuditError(f"{path}: expected a single trace JSON, got JSONL")
        if format == "auto":
            detected = detect_import_format(entries)
            if detected:
                return _load_import(
                    path, detected, git_repo=git_repo, baseline=baseline, workspace=workspace
                )
        if format == "claude-code" or (format == "auto" and _looks_like_claude_code(entries)):
            messages = _normalize_claude_code(entries)
            return [
                _trace_from_messages(
                    messages,
                    source=path,
                    agent="claude-code",
                    trace_id=_session_id(entries),
                    git_repo=git_repo,
                    baseline=baseline,
                    workspace=workspace,
                )
            ]
        return [
            _trace_from_messages(
                entries,
                source=path,
                agent="messages",
                trace_id=_messages_session_id(entries),
                git_repo=git_repo,
                baseline=baseline,
                workspace=workspace,
            )
        ]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuditError(f"{path}: invalid JSON ({exc})") from exc

    if format == "auto":
        detected = detect_import_format(data)
        if detected:
            return _load_import(
                path, detected, git_repo=git_repo, baseline=baseline, workspace=workspace
            )

    if format == "trace" or (
        format == "auto"
        and isinstance(data, dict)
        and {"id", "artifacts", "steps"} <= set(data)
    ):
        if not isinstance(data, dict):
            raise AuditError(f"{path}: expected a trace object")
        trace = Trace.from_dict(data)
        if not trace.artifacts:
            if workspace and baseline:
                trace.artifacts = workspace_artifacts(
                    [(step.tool, step.args) for step in trace.steps], baseline
                )
            elif git_repo:
                trace.artifacts = artifacts_from_git(git_repo)
            elif baseline and trace.steps:
                trace.artifacts = workspace_artifacts(
                    [(step.tool, step.args) for step in trace.steps], baseline
                )
        infer_test_evidence(trace)
        return [trace]

    if isinstance(data, dict) and "messages" in data:
        messages = data["messages"]
        trace_id = data.get("id")
        if not isinstance(messages, list):
            raise AuditError(f"{path}: 'messages' must be a list")
        if trace_id is None:
            trace_id = _messages_session_id(messages)
    elif isinstance(data, list):
        messages = data
        trace_id = _messages_session_id(messages)
    elif isinstance(data, dict) and data.get("type") in ("user", "assistant") and "message" in data:
        messages = _normalize_claude_code([data])
        trace_id = _session_id([data])
    else:
        raise AuditError(f"{path}: could not detect trace or message format")

    if format == "claude-code" or (format == "auto" and _looks_like_claude_code(messages)):
        messages = _normalize_claude_code(messages)
        agent = "claude-code"
    else:
        agent = "messages"

    return [
        _trace_from_messages(
            messages,
            source=path,
            agent=agent,
            trace_id=trace_id,
            git_repo=git_repo,
            baseline=baseline,
            workspace=workspace,
        )
    ]


def load_audit_traces(
    source: str | Path,
    *,
    format: str = "auto",
    git_repo: str | Path | None = None,
    baseline: str | Path | None = None,
    workspace: bool = False,
) -> list[Trace]:
    """Load traces from a trace JSON, transcript JSONL, messages JSON, or directory.

    ``workspace=True`` reads the current files instead of replaying edits on a
    pre-session baseline. Use it for hooks, where the working tree is post-session.
    """
    if format not in {
        "auto",
        "trace",
        "messages",
        "claude-code",
        "langsmith",
        "langfuse",
        "otel",
    }:
        raise AuditError(f"unknown format: {format}")
    source = Path(source)
    if not source.exists():
        raise AuditError(f"source not found: {source}")
    if source.is_dir():
        files = sorted(
            path for path in source.rglob("*") if path.suffix.lower() in (".json", ".jsonl")
        )
    else:
        files = [source]
    if not files:
        raise AuditError(f"no .json or .jsonl files found in {source}")

    traces: list[Trace] = []
    for path in files:
        traces.extend(
            _load_file(
                path,
                format=format,
                git_repo=git_repo,
                baseline=baseline,
                workspace=workspace,
            )
        )
    return traces


def build_audit_contract(baseline: str | Path = ".", run_tests: bool = False) -> Contract:
    data, _warning = build_contract(baseline)
    specs: list[dict[str, Any]] = []
    for spec in data["verifiers"]:
        if spec["name"] == "tests.pass" and not run_tests:
            continue
        if spec["name"] == "budget.steps":
            spec.setdefault("params", {})["max_steps"] = 200
        if spec["name"] == "diff.max_lines":
            spec.setdefault("params", {})["max_changed_lines"] = 400
        specs.append(spec)
    if run_tests and not any(spec["name"] == "tests.pass" for spec in specs):
        specs.append({"name": "tests.pass", "required": True})
    data["verifiers"] = specs
    data["name"] = f"audit-{Path(baseline).resolve().name}"
    data["fail_fast"] = False
    return Contract.from_dict(data)


@dataclass
class AuditFinding:
    trace_id: str
    verifier: str
    layer: str
    outcome: str
    severity: str
    reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "verifier": self.verifier,
            "layer": self.layer,
            "outcome": self.outcome,
            "severity": self.severity,
            "reasons": self.reasons,
            "evidence": self.evidence,
        }


@dataclass
class AuditReport:
    baseline: Path
    traces: list[Trace]
    findings: list[AuditFinding]
    suggested_contract: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def finding_trace_ids(self) -> set[str]:
        return {finding.trace_id for finding in self.findings}

    def clean_count(self) -> int:
        return len({trace.id for trace in self.traces} - self.finding_trace_ids())

    def severity_counts(self) -> dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def escalated_count(self) -> int:
        return sum(1 for finding in self.findings if finding.outcome == ESCALATE)

    def exit_code(self, fail_on: str = "any") -> int:
        if fail_on == "none" or not self.findings:
            return 0
        if fail_on == "high":
            return 1 if any(f.severity in {"critical", "high"} for f in self.findings) else 0
        return 1

    def write_contract(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.suggested_contract, indent=2) + "\n", encoding="utf-8")
        return target

    def to_dict(self) -> dict[str, Any]:
        counts = self.severity_counts()
        return {
            "baseline": str(self.baseline),
            "traces": len(self.traces),
            "summary": {
                **counts,
                "clean": self.clean_count(),
                "with_findings": len(self.finding_trace_ids()),
                "escalated": self.escalated_count(),
            },
            "findings": [finding.to_dict() for finding in self.findings],
            "suggested_contract": self.suggested_contract,
            "warnings": self.warnings,
        }


def audit_traces(
    contract: Contract,
    traces: Sequence[Trace],
    baseline: str | Path,
) -> AuditReport:
    findings: list[AuditFinding] = []
    warnings: list[str] = []
    for trace in traces:
        result = run_contract(contract, trace, baseline)
        for verdict in result.verdicts:
            if verdict.outcome in (FAIL, ESCALATE):
                findings.append(
                    AuditFinding(
                        trace_id=trace.id,
                        verifier=verdict.verifier,
                        layer=verdict.layer,
                        outcome=verdict.outcome,
                        severity=SEVERITY.get(verdict.verifier, "medium"),
                        reasons=verdict.reasons,
                        evidence=verdict.evidence,
                    )
                )
        if not trace.artifacts:
            warnings.append(f"{trace.id}: no artifacts; diff-based checks skipped")
    findings.sort(key=lambda f: (-_RANK.get(f.severity, 0), f.trace_id, f.verifier))
    return AuditReport(
        baseline=Path(baseline).resolve(),
        traces=list(traces),
        findings=findings,
        suggested_contract=contract.to_dict(),
        warnings=warnings,
    )


def render_audit(report: AuditReport, written_to: str | None = None) -> str:
    lines = [
        "Assaystone audit",
        f"baseline: {report.baseline}",
        f"traces: {len(report.traces)} "
        f"({report.clean_count()} clean, {len(report.finding_trace_ids())} with findings)",
    ]
    if not report.findings:
        lines.append("")
        lines.append("no findings")
    else:
        by_trace: dict[str, list[AuditFinding]] = {}
        for finding in report.findings:
            by_trace.setdefault(finding.trace_id, []).append(finding)
        for trace in report.traces:
            trace_findings = by_trace.get(trace.id)
            if not trace_findings:
                continue
            changed = ", ".join(artifact.path for artifact in trace.artifacts) or "(no artifacts)"
            lines.append("")
            lines.append(f"{trace.id}  changed: {changed}")
            for finding in trace_findings:
                reason = finding.reasons[0] if finding.reasons else ""
                if len(reason) > 110:
                    reason = reason[:107] + "..."
                label = "REVIEW" if finding.outcome == ESCALATE else finding.severity.upper()
                lines.append(f"  {label:<8} {finding.verifier:<24} {reason}")
    lines.append("")
    counts = report.severity_counts()
    lines.append(
        f"summary: {counts['critical']} critical, {counts['high']} high, "
        f"{counts['medium']} medium, {counts['low']} low"
    )
    if report.warnings:
        lines.append("")
        for warning in report.warnings:
            lines.append(f"warning: {warning}")
    lines.append("")
    if written_to:
        lines.append(f"suggested contract: {written_to}")
    else:
        lines.append("suggested contract: rerun with --write-contract .assaystone/contract.json")
    return "\n".join(lines)
