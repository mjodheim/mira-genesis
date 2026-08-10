"""Evaluator-owned M073 task generation and semantic checks.

This module is not part of the lineage skill capsule. It owns the project-authored bounded repair
family, task seeds and success semantics. The teacher runner does not import it, and the serialized
capsule contains none of its evaluator logic.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib


_ALLOWED_EVAL_NODES = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Assign, ast.Name, ast.Store, ast.Load,
    ast.Return, ast.If, ast.BinOp, ast.Div, ast.IfExp, ast.Compare, ast.NotEq, ast.Eq, ast.Constant,
    ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
)


@dataclass(frozen=True)
class RepairTask:
    task_id: str
    source: str
    function_name: str
    numerator_name: str
    denominator_name: str


def source_sha256(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def generate_division_repair_task(seed: int, *, split: str) -> RepairTask:
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("repair-task seed must be a non-negative integer")
    if split not in {"training", "holdout", "fixture"}:
        raise ValueError("repair-task split is unknown")
    digest = hashlib.sha256(f"m073:{split}:{seed}".encode()).hexdigest()
    function_name = f"ratio_{digest[:10]}"
    numerator = f"value_{digest[10:18]}"
    denominator = f"scale_{digest[18:26]}"
    marker = f"marker_{digest[26:34]}"
    source = (
        f"def {function_name}({numerator}, {denominator}):\n"
        f"    {marker} = {seed % 17}\n"
        f"    return {numerator} / {denominator}\n"
    )
    return RepairTask(
        task_id=f"m073-{split}-{seed}", source=source, function_name=function_name,
        numerator_name=numerator, denominator_name=denominator,
    )


def _parse(source: str) -> ast.Module:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError("evaluated M073 module does not parse") from exc
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_EVAL_NODES):
            raise ValueError(f"unsupported M073 evaluator node: {type(node).__name__}")
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1:
        raise ValueError("M073 evaluator requires exactly one function")
    return tree


def _function(tree: ast.Module) -> ast.FunctionDef:
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef))


def _prefix_signature(function: ast.FunctionDef) -> str:
    body = function.body
    if not body:
        raise ValueError("M073 function body is empty")
    prefix: list[ast.stmt]
    if len(body) >= 2 and isinstance(body[-2], ast.If) and isinstance(body[-1], ast.Return):
        guard = body[-2]
        if not guard.orelse and len(guard.body) == 1 and isinstance(guard.body[0], ast.Return):
            prefix = list(body[:-2])
        else:
            prefix = list(body[:-1])
    elif isinstance(body[-1], ast.If):
        final = body[-1]
        if not (
            len(final.body) == 1 and isinstance(final.body[0], ast.Return)
            and len(final.orelse) == 1 and isinstance(final.orelse[0], ast.Return)
        ):
            raise ValueError("M073 final conditional has unsupported control flow")
        prefix = list(body[:-1])
    elif isinstance(body[-1], ast.Return):
        prefix = list(body[:-1])
    else:
        raise ValueError("M073 function has unsupported terminal control flow")
    clone = ast.FunctionDef(
        name=function.name,
        args=function.args,
        body=prefix,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    return ast.dump(clone, include_attributes=False)


EVALUATION_CASES: tuple[tuple[float, float], ...] = (
    (12, 3), (-12, 3), (12, -3), (0, 5), (12, 0), (-12, 0), (0, 0),
)


def _execute(source: str, function_name: str, a: float, b: float) -> float | int:
    tree = _parse(source)
    namespace: dict[str, object] = {"__builtins__": {}}
    exec(compile(tree, "<m073-evaluator>", "exec"), namespace, namespace)  # noqa: S102
    candidate = namespace.get(function_name)
    if not callable(candidate):
        raise ValueError("M073 module does not expose the expected function")
    value = candidate(a, b)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("M073 function returned a non-numeric value")
    return value


def repair_passes(task: RepairTask, candidate_source: str) -> bool:
    try:
        original_tree = _parse(task.source)
        candidate_tree = _parse(candidate_source)
        original = _function(original_tree)
        candidate = _function(candidate_tree)
        if original.name != candidate.name:
            return False
        if ast.dump(original.args, include_attributes=False) != ast.dump(
            candidate.args, include_attributes=False
        ):
            return False
        if _prefix_signature(original) != _prefix_signature(candidate):
            return False
        for numerator, denominator in EVALUATION_CASES:
            observed = _execute(candidate_source, task.function_name, numerator, denominator)
            expected = numerator / denominator if denominator != 0 else 0
            if observed != expected:
                return False
    except (ValueError, ZeroDivisionError, TypeError):
        return False
    return True


__all__ = [
    "EVALUATION_CASES", "RepairTask", "generate_division_repair_task", "repair_passes",
    "source_sha256",
]
