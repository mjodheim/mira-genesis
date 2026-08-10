"""Bounded model-to-lineage skill appropriation primitives for M073.

The teacher may provide complete repaired training modules. It never provides a generalized
rewrite. This module extracts one parameterized terminal-return transformation from multiple
consistent demonstrations, serializes it, and can later apply it without importing a task
evaluator or calling a model backend.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence


_SLOT_PREFIX = "__MIRA_SLOT_"
_ALLOWED_NODES = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Assign, ast.Name, ast.Store, ast.Load,
    ast.Return, ast.If, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.Pow, ast.IfExp, ast.Compare, ast.NotEq, ast.Eq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Constant, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd, ast.BoolOp, ast.And, ast.Or, ast.Expr,
)


class SkillInductionError(ValueError):
    """Raised when demonstrations cannot justify one safe deterministic capsule."""


@dataclass(frozen=True)
class SkillDemonstration:
    task_id: str
    source: str
    repaired: str


@dataclass(frozen=True)
class SkillCapsule:
    skill_id: str
    source_pattern: str
    target_template: str
    preconditions: tuple[str, ...]
    training_evidence_sha256: str
    induction_trace_sha256: str
    provenance: str
    capsule_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "mira-skill-capsule-v1",
            "skill_id": self.skill_id,
            "source_pattern": self.source_pattern,
            "target_template": self.target_template,
            "preconditions": list(self.preconditions),
            "training_evidence_sha256": self.training_evidence_sha256,
            "induction_trace_sha256": self.induction_trace_sha256,
            "provenance": self.provenance,
            "capsule_sha256": self.capsule_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "SkillCapsule":
        if value.get("schema") != "mira-skill-capsule-v1":
            raise SkillInductionError("unexpected skill-capsule schema")
        preconditions = value.get("preconditions")
        if not isinstance(preconditions, list) or not all(
            isinstance(item, str) for item in preconditions
        ):
            raise SkillInductionError("skill capsule preconditions are malformed")
        capsule = cls(
            skill_id=str(value["skill_id"]),
            source_pattern=str(value["source_pattern"]),
            target_template=str(value["target_template"]),
            preconditions=tuple(preconditions),
            training_evidence_sha256=str(value["training_evidence_sha256"]),
            induction_trace_sha256=str(value["induction_trace_sha256"]),
            provenance=str(value["provenance"]),
            capsule_sha256=str(value["capsule_sha256"]),
        )
        if capsule.capsule_sha256 != _capsule_digest(capsule):
            raise SkillInductionError("skill capsule digest mismatch")
        return capsule


class TeacherCallTrap:
    """Evaluation sentinel: any post-removal teacher invocation is an experiment failure."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, *_args: object, **_kwargs: object) -> str:
        self.calls += 1
        raise RuntimeError("external teacher is forbidden after the M073 removal boundary")


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _parse_safe_module(source: str) -> ast.Module:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise SkillInductionError("Python module does not parse") from exc
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise SkillInductionError(
                f"unsupported Python node in bounded skill domain: {type(node).__name__}"
            )
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1:
        raise SkillInductionError("bounded skill module must contain exactly one function")
    if any(isinstance(node, ast.Expr) for node in tree.body):
        raise SkillInductionError("bounded skill module forbids top-level expressions")
    return tree


def _function(tree: ast.Module) -> ast.FunctionDef:
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
    if function.decorator_list or function.returns or function.type_comment:
        raise SkillInductionError("bounded skill function forbids decorators and annotations")
    if function.args.vararg or function.args.kwarg or function.args.kwonlyargs:
        raise SkillInductionError("bounded skill function requires fixed positional arguments")
    return function


def _return_value(statement: ast.stmt) -> ast.expr:
    if not isinstance(statement, ast.Return) or statement.value is None:
        raise SkillInductionError("bounded rewrite region requires value-return statements")
    return statement.value


def _rewrite_region(function: ast.FunctionDef) -> tuple[ast.expr, list[ast.stmt]]:
    """Normalize one terminal return region to an expression plus unchanged prefix.

    Accepted shapes are deliberately small and task-agnostic: one final return, a final if with one
    return in each branch, or a guard-if with one return followed by a final return. Conditional
    control flow is represented as an IfExp only for induction; teacher syntax itself is not copied.
    """

    body = function.body
    if not body:
        raise SkillInductionError("bounded skill function has no executable body")
    if len(body) >= 2 and isinstance(body[-2], ast.If) and isinstance(body[-1], ast.Return):
        guard = body[-2]
        if not guard.orelse and len(guard.body) == 1 and isinstance(guard.body[0], ast.Return):
            return ast.IfExp(
                test=copy.deepcopy(guard.test),
                body=copy.deepcopy(_return_value(guard.body[0])),
                orelse=copy.deepcopy(_return_value(body[-1])),
            ), list(body[:-2])
    final = body[-1]
    if isinstance(final, ast.If):
        if (
            len(final.body) == 1 and isinstance(final.body[0], ast.Return)
            and len(final.orelse) == 1 and isinstance(final.orelse[0], ast.Return)
        ):
            return ast.IfExp(
                test=copy.deepcopy(final.test),
                body=copy.deepcopy(_return_value(final.body[0])),
                orelse=copy.deepcopy(_return_value(final.orelse[0])),
            ), list(body[:-1])
        raise SkillInductionError("bounded final if must contain exactly one return per branch")
    if isinstance(final, ast.Return):
        return copy.deepcopy(_return_value(final)), list(body[:-1])
    raise SkillInductionError("bounded skill function lacks a supported terminal return region")


def _prefix_dump(function: ast.FunctionDef, prefix: Sequence[ast.stmt]) -> str:
    clone = copy.deepcopy(function)
    clone.body = [copy.deepcopy(node) for node in prefix]
    return ast.dump(clone, annotate_fields=True, include_attributes=False)


class _Slotter(ast.NodeTransformer):
    def __init__(self, bindings: Mapping[str, str] | None = None) -> None:
        self.concrete_to_slot = dict(bindings or {})

    def visit_Name(self, node: ast.Name) -> ast.AST:
        slot = self.concrete_to_slot.get(node.id)
        if slot is None:
            slot = f"{_SLOT_PREFIX}{len(self.concrete_to_slot)}__"
            self.concrete_to_slot[node.id] = slot
        return ast.copy_location(ast.Name(id=slot, ctx=copy.deepcopy(node.ctx)), node)


def _abstract_expression(
    expression: ast.expr, *, bindings: Mapping[str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    slotter = _Slotter(bindings)
    rewritten = slotter.visit(copy.deepcopy(expression))
    ast.fix_missing_locations(rewritten)
    return ast.unparse(rewritten), dict(slotter.concrete_to_slot)


def _abstract_target(expression: ast.expr, concrete_to_slot: Mapping[str, str]) -> str:
    class TargetSlotter(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            slot = concrete_to_slot.get(node.id)
            if slot is None:
                raise SkillInductionError(
                    "teacher repair introduced an identifier absent from the source expression"
                )
            return ast.copy_location(ast.Name(id=slot, ctx=copy.deepcopy(node.ctx)), node)

    rewritten = TargetSlotter().visit(copy.deepcopy(expression))
    ast.fix_missing_locations(rewritten)
    return ast.unparse(rewritten)


def _capsule_digest(capsule: SkillCapsule) -> str:
    value = {
        "schema": "mira-skill-capsule-v1",
        "skill_id": capsule.skill_id,
        "source_pattern": capsule.source_pattern,
        "target_template": capsule.target_template,
        "preconditions": list(capsule.preconditions),
        "training_evidence_sha256": capsule.training_evidence_sha256,
        "induction_trace_sha256": capsule.induction_trace_sha256,
        "provenance": capsule.provenance,
    }
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def induce_skill_capsule(
    demonstrations: Sequence[SkillDemonstration], *,
    skill_id: str = "m073-induced-return-rewrite-v1",
) -> SkillCapsule:
    """Induce exactly one alpha-generalized terminal-return rewrite from demonstrations."""

    if len(demonstrations) < 4:
        raise SkillInductionError("skill induction requires at least four demonstrations")
    if len({demo.task_id for demo in demonstrations}) != len(demonstrations):
        raise SkillInductionError("teacher demonstrations require unique task identifiers")

    source_patterns: list[str] = []
    target_templates: list[str] = []
    trace: list[dict[str, object]] = []
    evidence: list[dict[str, str]] = []
    for demonstration in demonstrations:
        before_tree = _parse_safe_module(demonstration.source)
        after_tree = _parse_safe_module(demonstration.repaired)
        before_function = _function(before_tree)
        after_function = _function(after_tree)
        if before_function.name != after_function.name:
            raise SkillInductionError("teacher repair changed the function name")
        if ast.dump(before_function.args, include_attributes=False) != ast.dump(
            after_function.args, include_attributes=False
        ):
            raise SkillInductionError("teacher repair changed the function signature")
        before_expression, before_prefix = _rewrite_region(before_function)
        after_expression, after_prefix = _rewrite_region(after_function)
        if _prefix_dump(before_function, before_prefix) != _prefix_dump(
            after_function, after_prefix
        ):
            raise SkillInductionError(
                "teacher repair changed content outside the terminal return region"
            )
        source_pattern, concrete_to_slot = _abstract_expression(before_expression)
        target_template = _abstract_target(after_expression, concrete_to_slot)
        if source_pattern == target_template:
            raise SkillInductionError("teacher demonstration contains no executable transformation")
        source_patterns.append(source_pattern)
        target_templates.append(target_template)
        evidence.append({
            "task_id": demonstration.task_id,
            "source_sha256": hashlib.sha256(demonstration.source.encode("utf-8")).hexdigest(),
            "repair_sha256": hashlib.sha256(demonstration.repaired.encode("utf-8")).hexdigest(),
        })
        trace.append({
            "task_id": demonstration.task_id,
            "source_pattern": source_pattern,
            "target_template": target_template,
            "slot_count": len(concrete_to_slot),
        })

    if len(set(source_patterns)) != 1 or len(set(target_templates)) != 1:
        raise SkillInductionError(
            "teacher demonstrations do not justify one unique generalized rewrite"
        )
    provisional = SkillCapsule(
        skill_id=skill_id,
        source_pattern=source_patterns[0],
        target_template=target_templates[0],
        preconditions=(
            "one safe Python function",
            "one supported terminal return region",
            "source expression structurally matches the learned alpha-template",
            "all target identifiers bind to source-expression roles",
        ),
        training_evidence_sha256=_sha256(evidence),
        induction_trace_sha256=_sha256(trace),
        provenance="induced_from_external_demonstrations",
        capsule_sha256="",
    )
    return SkillCapsule(**{**provisional.__dict__, "capsule_sha256": _capsule_digest(provisional)})


def apply_skill_capsule(capsule: SkillCapsule, source: str) -> str:
    """Apply a serialized capsule by structural matching and lineage-chosen bindings."""

    if capsule.capsule_sha256 != _capsule_digest(capsule):
        raise SkillInductionError("skill capsule digest mismatch before application")
    tree = _parse_safe_module(source)
    function = _function(tree)
    observed_expression, prefix = _rewrite_region(function)
    observed_pattern, concrete_to_slot = _abstract_expression(observed_expression)
    if observed_pattern != capsule.source_pattern:
        raise SkillInductionError("held-out source does not satisfy capsule preconditions")
    slot_to_concrete = {slot: concrete for concrete, slot in concrete_to_slot.items()}
    try:
        target_expr = ast.parse(capsule.target_template, mode="eval").body
    except SyntaxError as exc:
        raise SkillInductionError("skill capsule target template does not parse") from exc

    class Binder(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id.startswith(_SLOT_PREFIX):
                concrete = slot_to_concrete.get(node.id)
                if concrete is None:
                    raise SkillInductionError("skill capsule references an unbound identifier role")
                return ast.copy_location(ast.Name(id=concrete, ctx=copy.deepcopy(node.ctx)), node)
            return node

    instantiated = Binder().visit(copy.deepcopy(target_expr))
    ast.fix_missing_locations(instantiated)
    function.body = [copy.deepcopy(node) for node in prefix] + [ast.Return(value=instantiated)]
    ast.fix_missing_locations(tree)
    rewritten = ast.unparse(tree) + "\n"
    _parse_safe_module(rewritten)
    return rewritten


__all__ = [
    "SkillCapsule", "SkillDemonstration", "SkillInductionError", "TeacherCallTrap",
    "apply_skill_capsule", "induce_skill_capsule",
]
