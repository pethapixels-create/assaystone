"""Mutation testing for verification contracts.

Inject one plausible defect at a time into the agent's artifacts, run the
contract, and report whether it was killed. Survivors are either equivalent
mutants or real gaps in the verifier set.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contract import Contract
from .model import ESCALATE, FAIL, Artifact, Trace
from .runner import run_contract

FLIP_OPS: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}


@dataclass
class Mutant:
    id: str
    operator: str
    target: str
    description: str
    artifacts: list[Artifact]


@dataclass
class MutationResult:
    mutant: Mutant
    status: str  # killed | survived | escalated | invalid
    killed_by: str | None = None
    detail: str = ""


@dataclass
class MutationSummary:
    contract: str
    results: list[MutationResult] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        counts = {"killed": 0, "survived": 0, "escalated": 0, "invalid": 0}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
        return counts

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def score(self) -> float:
        counts = self.counts()
        denominator = counts["killed"] + counts["survived"]
        return counts["killed"] / denominator if denominator else 0.0

    def by_operator(self) -> dict[str, tuple[int, int]]:
        out: dict[str, tuple[int, int]] = {}
        for result in self.results:
            if result.status == "invalid":
                continue
            killed, total = out.get(result.mutant.operator, (0, 0))
            out[result.mutant.operator] = (
                killed + (1 if result.status == "killed" else 0),
                total + 1,
            )
        return out

    def survivors(self) -> list[MutationResult]:
        return [result for result in self.results if result.status == "survived"]


def _walk(node: ast.AST, path: tuple[tuple[str, int | None], ...] = ()):
    yield path, node
    for name, value in ast.iter_fields(node):
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, ast.AST):
                    yield from _walk(item, path + ((name, index),))
        elif isinstance(value, ast.AST):
            yield from _walk(value, path + ((name, None),))


def _node_at(root: ast.AST, path: tuple[tuple[str, int | None], ...]) -> ast.AST:
    node: Any = root
    for name, index in path:
        node = getattr(node, name)
        if index is not None:
            node = node[index]
    return node


def _render(tree: ast.AST) -> str:
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _source_candidates(tree: ast.AST) -> list[tuple[str, tuple, int, str]]:
    out: list[tuple[str, tuple, int, str]] = []
    functions: list[tuple[tuple, ast.AST]] = []
    for path, node in _walk(tree):
        lineno = getattr(node, "lineno", 0)
        if isinstance(node, ast.Compare) and node.ops and type(node.ops[0]) in FLIP_OPS:
            out.append(("compare_flip", path, lineno, f"flip comparison at line {lineno}"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            out.append(
                (
                    "const_off_by_one",
                    path,
                    lineno,
                    f"change constant {node.value} -> {node.value + 1} at line {lineno}",
                )
            )
        elif isinstance(node, ast.Return) and node.value is not None:
            out.append(("return_none", path, lineno, f"return None at line {lineno}"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append((path, node))
            out.append(("insert_print", path, lineno, f"insert print() in {node.name} at line {lineno}"))
        elif isinstance(node, ast.If):
            out.append(("invert_if", path, lineno, f"invert condition at line {lineno}"))

    for function_path, function in functions:
        if len(function.body) <= 1:
            continue
        for index, statement in enumerate(function.body):
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            ):
                continue  # docstring
            lineno = getattr(statement, "lineno", 0)
            out.append(
                (
                    "delete_statement",
                    function_path + (("body", index),),
                    lineno,
                    f"delete statement at line {lineno}",
                )
            )
    return out


def _apply(tree: ast.AST, path: tuple, operator: str) -> None:
    node = _node_at(tree, path)
    if operator == "compare_flip":
        node.ops[0] = FLIP_OPS[type(node.ops[0])]()  # type: ignore[attr-defined]
    elif operator == "const_off_by_one":
        node.value = node.value + 1  # type: ignore[attr-defined]
    elif operator == "return_none":
        node.value = ast.Constant(value=None)  # type: ignore[attr-defined]
    elif operator == "insert_print":
        statement = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="print", ctx=ast.Load()),
                args=[ast.Constant(value="debug")],
                keywords=[],
            )
        )
        node.body.insert(0, statement)  # type: ignore[attr-defined]
    elif operator == "invert_if":
        node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)  # type: ignore[attr-defined]
    elif operator == "delete_statement":
        parent = _node_at(tree, path[:-1])
        field, index = path[-1]
        del getattr(parent, field)[index]
    else:
        raise ValueError(f"unknown mutation operator: {operator}")


def _source_mutants(trace: Trace, per_operator: int = 4, budget: int = 18) -> list[Mutant]:
    mutants: list[Mutant] = []
    counts: dict[str, int] = {}
    for artifact in trace.artifacts:
        if artifact.change == "deleted" or not artifact.path.endswith(".py"):
            continue
        try:
            tree = ast.parse(artifact.content, filename=artifact.path)
        except SyntaxError:
            continue
        for operator, path, lineno, description in _source_candidates(tree):
            if len(mutants) >= budget:
                return mutants
            if counts.get(operator, 0) >= per_operator:
                continue
            mutant_tree = copy.deepcopy(tree)
            try:
                _apply(mutant_tree, path, operator)
                source = _render(mutant_tree)
                ast.parse(source)
            except Exception:
                continue
            counts[operator] = counts.get(operator, 0) + 1
            mutants.append(
                Mutant(
                    id=f"{operator}-{len(mutants):02d}",
                    operator=operator,
                    target=f"{artifact.path}:{lineno}",
                    description=description,
                    artifacts=[Artifact(path=artifact.path, content=source, change=artifact.change)],
                )
            )
    return mutants


def _current_content(trace: Trace, baseline: Path, rel: str) -> str | None:
    artifact = trace.artifact_map().get(rel)
    if artifact is not None and artifact.change != "deleted":
        return artifact.content
    path = baseline / rel
    return path.read_text(encoding="utf-8") if path.exists() else None


def _remove_test_method(source: str, preferred: str = "test_round_half_cent") -> tuple[str, str] | None:
    tree = ast.parse(source)
    target = None
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    for cls in classes:
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == preferred:
                target = node
                break
        if target is not None:
            break
    if target is None:
        for cls in classes:
            for node in cls.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                    target = node
                    break
            if target is not None:
                break
    if target is None:
        return None
    lines = source.splitlines(keepends=True)
    start = (target.decorator_list[0].lineno - 1) if target.decorator_list else target.lineno - 1
    end = target.end_lineno or target.lineno
    if end < len(lines) and lines[end].strip() == "":
        end += 1
    return "".join(lines[:start] + lines[end:]), target.name


def _weaken_assert(source: str) -> str | None:
    lines = source.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if "self.assertEqual(" in line:
            indent = line[: len(line) - len(line.lstrip())]
            lines[index] = f"{indent}self.assertTrue(True)  # weakened assertion\n"
            return "".join(lines)
    return None


def _artifact_mutants(trace: Trace, baseline: Path) -> list[Mutant]:
    mutants: list[Mutant] = []
    baseline = Path(baseline).resolve()

    ci_dir = baseline / "ci"
    ci_files = sorted(path for path in ci_dir.rglob("*") if path.is_file()) if ci_dir.exists() else []
    if ci_files:
        target = ci_files[0]
        rel = target.relative_to(baseline).as_posix()
        content = _current_content(trace, baseline, rel)
        if content is not None:
            mutants.append(
                Mutant(
                    id="touch_forbidden_file-00",
                    operator="touch_forbidden_file",
                    target=rel,
                    description=f"modify forbidden file {rel}",
                    artifacts=[Artifact(rel, content + "\n# mutant: touched a forbidden path\n", "modified")],
                )
            )

    tests_dir = baseline / "tests"
    test_files = sorted(tests_dir.rglob("test_*.py")) if tests_dir.exists() else []
    if test_files:
        target = test_files[0]
        rel = target.relative_to(baseline).as_posix()
        source = _current_content(trace, baseline, rel)
        if source is not None:
            removed = _remove_test_method(source)
            if removed is not None:
                new_source, method_name = removed
                mutants.append(
                    Mutant(
                        id="delete_test_method-00",
                        operator="delete_test_method",
                        target=f"{rel}::{method_name}",
                        description=f"delete test method {method_name}",
                        artifacts=[Artifact(rel, new_source, "modified")],
                    )
                )
            weakened = _weaken_assert(source)
            if weakened is not None:
                mutants.append(
                    Mutant(
                        id="weaken_assert-00",
                        operator="weaken_assert",
                        target=rel,
                        description="replace assertEqual with assertTrue(True)",
                        artifacts=[Artifact(rel, weakened, "modified")],
                    )
                )
    return mutants


def generate_mutants(trace: Trace, baseline: str | Path, max_total: int = 18) -> list[Mutant]:
    artifact_mutants = _artifact_mutants(trace, Path(baseline))
    source_budget = max(1, max_total - len(artifact_mutants))
    source_mutants = _source_mutants(trace, budget=source_budget)
    return (source_mutants + artifact_mutants)[:max_total]


def run_mutation(
    contract: Contract,
    trace: Trace,
    baseline: str | Path,
    max_total: int = 18,
) -> MutationSummary:
    summary = MutationSummary(contract=contract.name)
    for mutant in generate_mutants(trace, baseline, max_total=max_total):
        mutated = trace.with_artifacts(mutant.artifacts)
        try:
            run = run_contract(contract, mutated, baseline)
        except Exception as exc:  # noqa: BLE001 - invalid mutants are excluded from the score
            summary.results.append(MutationResult(mutant, "invalid", detail=repr(exc)))
            continue
        if run.verdict == FAIL:
            status = "killed"
        elif run.verdict == ESCALATE:
            status = "escalated"
        else:
            status = "survived"
        summary.results.append(MutationResult(mutant, status, killed_by=run.first_failure))
    return summary
