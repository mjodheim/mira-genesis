"""M020 — bounded self-rewrite with internal tools and proof-gated adoption.

This module does not grant an organism unrestricted shell access. It implements the
smallest testable core required before such power could be discussed responsibly:

1. executable policy code is treated as the current cognitive body;
2. the organism owns a registry of source-rewrite tools;
3. those tools propose candidate bodies without seeing held-out answers;
4. every candidate is parsed, safety-checked, compiled and evaluated in isolation;
5. a candidate is adopted only when it strictly improves the declared development
   objective;
6. the previous body is archived exactly and can be restored;
7. an accepted multi-edit patch becomes a reusable learned rewrite tool.

The accepted language is deliberately finite and loop-free. That makes candidate
execution terminating and keeps the experiment decidable. Later experiments may widen
the language only after preserving the same isolation and rollback guarantees.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import hashlib
from typing import Iterable, Protocol, Sequence


_ALLOWED_NODE_TYPES = (
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.If,
    ast.Assign,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.FloorDiv,
    ast.Mod,
    ast.USub,
    ast.UAdd,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
)

_BINARY_OPERATORS: dict[str, type[ast.operator]] = {
    "add": ast.Add,
    "sub": ast.Sub,
    "mul": ast.Mult,
    "floordiv": ast.FloorDiv,
    "mod": ast.Mod,
}

_COMPARISON_OPERATORS: dict[str, type[ast.cmpop]] = {
    "eq": ast.Eq,
    "ne": ast.NotEq,
    "lt": ast.Lt,
    "le": ast.LtE,
    "gt": ast.Gt,
    "ge": ast.GtE,
}


class UnsafeSource(ValueError):
    """Raised when a candidate leaves the bounded policy language."""


@dataclass(frozen=True)
class Case:
    arguments: tuple[int, ...]
    expected: int


@dataclass(frozen=True)
class Evaluation:
    passed: int
    total: int
    failures: tuple[str, ...] = ()

    @property
    def perfect(self) -> bool:
        return self.passed == self.total


@dataclass(frozen=True)
class PatchOperation:
    """A serialisable edit in the organism's rewrite language."""

    kind: str
    index: int
    value: int | str

    def key(self) -> tuple[str, int, int | str]:
        return self.kind, self.index, self.value


@dataclass(frozen=True)
class RewriteCandidate:
    source: str
    trace: tuple[PatchOperation, ...]
    development: Evaluation

    @property
    def digest(self) -> str:
        return source_digest(self.source)


@dataclass(frozen=True)
class RewriteResult:
    adopted: bool
    reason: str
    baseline: RewriteCandidate
    selected: RewriteCandidate
    candidates_evaluated: int
    learned_tool: str | None


class RewriteTool(Protocol):
    name: str

    def propose(self, source: str) -> Iterable[tuple[PatchOperation, ...]]: ...


class _IndexedNodeTransformer(ast.NodeTransformer):
    def __init__(self, operation: PatchOperation) -> None:
        self.operation = operation
        self.position = -1
        self.applied = False

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if self.operation.kind != "constant" or type(node.value) is not int:
            return node
        self.position += 1
        if self.position == self.operation.index:
            self.applied = True
            return ast.copy_location(ast.Constant(int(self.operation.value)), node)
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        node = self.generic_visit(node)
        if self.operation.kind != "binary_operator":
            return node
        self.position += 1
        if self.position == self.operation.index:
            operator = _BINARY_OPERATORS.get(str(self.operation.value))
            if operator is None:
                raise ValueError(f"unknown binary operator: {self.operation.value}")
            self.applied = True
            node.op = operator()
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        node = self.generic_visit(node)
        if self.operation.kind != "comparison_operator":
            return node
        if len(node.ops) != 1:
            return node
        self.position += 1
        if self.position == self.operation.index:
            operator = _COMPARISON_OPERATORS.get(str(self.operation.value))
            if operator is None:
                raise ValueError(f"unknown comparison operator: {self.operation.value}")
            self.applied = True
            node.ops = [operator()]
        return node


def source_digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def validate_source(source: str, function_name: str) -> ast.Module:
    """Parse and prove that a candidate belongs to the terminating policy subset."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise UnsafeSource(f"syntax error: {error.msg}") from error

    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(tree.body) != 1 or len(functions) != 1:
        raise UnsafeSource("a policy module must contain exactly one function")
    function = functions[0]
    if function.name != function_name:
        raise UnsafeSource(f"expected function {function_name!r}")
    if function.decorator_list:
        raise UnsafeSource("decorators are not allowed")
    if function.args.vararg or function.args.kwarg or function.args.kwonlyargs:
        raise UnsafeSource("variadic and keyword-only arguments are not allowed")

    argument_names = {argument.arg for argument in function.args.args}
    assigned_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise UnsafeSource(f"node type {type(node).__name__} is not allowed")
        if isinstance(node, ast.Constant) and type(node.value) not in (int, bool, type(None)):
            raise UnsafeSource("only integer, boolean and None constants are allowed")
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise UnsafeSource("assignments must target one local name")
            assigned_names.add(node.targets[0].id)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in argument_names and node.id not in assigned_names:
                raise UnsafeSource(f"unknown name {node.id!r}")

    return tree


def apply_patch(source: str, operations: Sequence[PatchOperation]) -> str:
    tree = ast.parse(source)
    for operation in operations:
        transformer = _IndexedNodeTransformer(operation)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)
        if not transformer.applied:
            raise ValueError(f"operation did not match a node: {operation}")
    return ast.unparse(tree).strip() + "\n"


def compile_policy(source: str, function_name: str):
    tree = validate_source(source, function_name)
    namespace: dict[str, object] = {"__builtins__": {}}
    exec(compile(tree, "<m020-candidate>", "exec"), namespace, namespace)
    function = namespace[function_name]
    if not callable(function):
        raise UnsafeSource("the declared policy is not callable")
    return function


def evaluate_source(source: str, function_name: str, cases: Sequence[Case]) -> Evaluation:
    try:
        function = compile_policy(source, function_name)
    except (UnsafeSource, ValueError, TypeError) as error:
        return Evaluation(0, len(cases), (f"compile:{error}",))

    passed = 0
    failures: list[str] = []
    for index, case in enumerate(cases):
        try:
            value = function(*case.arguments)
        except Exception as error:  # The language is bounded; runtime faults still reject.
            failures.append(f"case[{index}]:{type(error).__name__}")
            continue
        if type(value) is not int:
            failures.append(f"case[{index}]:non_integer_result")
            continue
        if value == case.expected:
            passed += 1
        else:
            failures.append(f"case[{index}]:expected={case.expected},actual={value}")
    return Evaluation(passed, len(cases), tuple(failures))


@dataclass(frozen=True)
class ConstantRewriteTool:
    values: tuple[int, ...] = (-2, -1, 0, 1, 2, 3, 4)
    name: str = "replace_integer_constant"

    def propose(self, source: str) -> Iterable[tuple[PatchOperation, ...]]:
        tree = ast.parse(source)
        constants = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and type(node.value) is int
        ]
        for index, current in enumerate(constants):
            for value in self.values:
                if value != current:
                    yield (PatchOperation("constant", index, value),)


@dataclass(frozen=True)
class BinaryOperatorRewriteTool:
    name: str = "replace_binary_operator"

    def propose(self, source: str) -> Iterable[tuple[PatchOperation, ...]]:
        tree = ast.parse(source)
        operators = [node.op for node in ast.walk(tree) if isinstance(node, ast.BinOp)]
        for index, current in enumerate(operators):
            for name, operator in _BINARY_OPERATORS.items():
                if not isinstance(current, operator):
                    yield (PatchOperation("binary_operator", index, name),)


@dataclass(frozen=True)
class ComparisonOperatorRewriteTool:
    name: str = "replace_comparison_operator"

    def propose(self, source: str) -> Iterable[tuple[PatchOperation, ...]]:
        tree = ast.parse(source)
        comparisons = [
            node.ops[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Compare) and len(node.ops) == 1
        ]
        for index, current in enumerate(comparisons):
            for name, operator in _COMPARISON_OPERATORS.items():
                if not isinstance(current, operator):
                    yield (PatchOperation("comparison_operator", index, name),)


@dataclass(frozen=True)
class LearnedRewriteTool:
    name: str
    operations: tuple[PatchOperation, ...]

    def propose(self, source: str) -> Iterable[tuple[PatchOperation, ...]]:
        try:
            apply_patch(source, self.operations)
        except (SyntaxError, ValueError):
            return ()
        return (self.operations,)


@dataclass
class ToolRegistry:
    """The organism's internal tool surface, including tools it has learned."""

    primitives: tuple[RewriteTool, ...] = (
        ConstantRewriteTool(),
        BinaryOperatorRewriteTool(),
        ComparisonOperatorRewriteTool(),
    )
    learned: list[LearnedRewriteTool] = field(default_factory=list)

    def tools(self) -> tuple[RewriteTool, ...]:
        return self.primitives + tuple(self.learned)

    def absorb(self, operations: Sequence[PatchOperation]) -> LearnedRewriteTool:
        digest = hashlib.sha256(
            repr(tuple(operation.key() for operation in operations)).encode("utf-8")
        ).hexdigest()[:12]
        name = f"learned_patch_{digest}"
        for tool in self.learned:
            if tool.name == name:
                return tool
        tool = LearnedRewriteTool(name, tuple(operations))
        self.learned.append(tool)
        return tool


class SelfRewriteEngine:
    """Search candidate bodies and adopt only strict, deterministic improvements."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        max_edits: int = 2,
        beam_width: int = 32,
    ) -> None:
        if max_edits < 1:
            raise ValueError("max_edits must be positive")
        if beam_width < 1:
            raise ValueError("beam_width must be positive")
        self.registry = registry or ToolRegistry()
        self.max_edits = max_edits
        self.beam_width = beam_width

    @staticmethod
    def _rank_key(candidate: RewriteCandidate) -> tuple[int, int, str]:
        return (-candidate.development.passed, len(candidate.trace), candidate.digest)

    def improve(
        self,
        source: str,
        function_name: str,
        development_cases: Sequence[Case],
    ) -> RewriteResult:
        baseline_evaluation = evaluate_source(source, function_name, development_cases)
        baseline = RewriteCandidate(source, (), baseline_evaluation)
        best = baseline
        frontier = [baseline]
        seen = {baseline.digest}
        evaluated = 1

        for _depth in range(1, self.max_edits + 1):
            next_generation: list[RewriteCandidate] = []
            for parent in frontier:
                for tool in self.registry.tools():
                    for proposed in tool.propose(parent.source):
                        trace = parent.trace + tuple(proposed)
                        if len(trace) > self.max_edits:
                            continue
                        try:
                            candidate_source = apply_patch(parent.source, proposed)
                            validate_source(candidate_source, function_name)
                        except (SyntaxError, UnsafeSource, ValueError, TypeError):
                            continue
                        digest = source_digest(candidate_source)
                        if digest in seen:
                            continue
                        seen.add(digest)
                        evaluation = evaluate_source(
                            candidate_source, function_name, development_cases
                        )
                        candidate = RewriteCandidate(candidate_source, trace, evaluation)
                        evaluated += 1
                        next_generation.append(candidate)
                        if self._rank_key(candidate) < self._rank_key(best):
                            best = candidate

            next_generation.sort(key=self._rank_key)
            frontier = next_generation[: self.beam_width]
            if not frontier or best.development.perfect:
                break

        if best.development.passed <= baseline.development.passed:
            return RewriteResult(
                False,
                "no_strict_development_improvement",
                baseline,
                baseline,
                evaluated,
                None,
            )

        learned = self.registry.absorb(best.trace)
        return RewriteResult(
            True,
            "strict_development_improvement",
            baseline,
            best,
            evaluated,
            learned.name,
        )


@dataclass
class VersionedCodeBody:
    """An active executable body with exact archive and rollback semantics."""

    function_name: str
    active_source: str
    archive: list[str] = field(default_factory=list)
    adopted_digests: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        validate_source(self.active_source, self.function_name)
        if not self.adopted_digests:
            self.adopted_digests.append(source_digest(self.active_source))

    def adopt(self, result: RewriteResult) -> bool:
        if not result.adopted:
            return False
        if source_digest(self.active_source) != result.baseline.digest:
            raise ValueError("rewrite result does not descend from the active body")
        validate_source(result.selected.source, self.function_name)
        self.archive.append(self.active_source)
        self.active_source = result.selected.source
        self.adopted_digests.append(result.selected.digest)
        return True

    def rollback(self) -> bool:
        if not self.archive:
            return False
        self.active_source = self.archive.pop()
        self.adopted_digests.append(source_digest(self.active_source))
        return True

    def run(self, *arguments: int) -> int:
        value = compile_policy(self.active_source, self.function_name)(*arguments)
        if type(value) is not int:
            raise TypeError("policy returned a non-integer result")
        return value
