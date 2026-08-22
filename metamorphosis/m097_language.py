"""M097: a state-owned extension to the real-software repair-operation language.

The inherited M094/M096 mapping operations can only place one object field (possibly
under a unary wrapper or renderer call) at each output key.  No composition of those
independent decisions can create a binary expression.  M097 encounters a mapping value
such as ``self.stop - self.start``, proves that structural gap, assembles a symbolic
expression program from smaller stack instructions, registers it in serialized language
state, and interprets it as one new repair operation.

The substrate contains instruction semantics, not a finished derived-field operation.
Field and key names are always recovered from the observed demand.
"""

from __future__ import annotations

import ast
import hashlib
import itertools
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from metamorphosis import m094_composition as inherited
from metamorphosis.m094_composition import MappingItem, MethodDraft, Operation

LANGUAGE_SCHEMA = "m097-operation-language-v1"
DEFINITION_SCHEMA = "m097-expression-operation-v1"
ASSEMBLY_TOKENS = (
    "PUSH_LEFT",
    "PUSH_RIGHT",
    "ADD",
    "SUB",
    "MUL",
    "NEG",
    "SWAP",
)
MAX_ASSEMBLY_LENGTH = 4
EXTENSION_WRAPPER = "m097-expression:"


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class DerivedRequirement:
    class_name: str
    key: str
    left_field: str
    operator: str
    right_field: str
    demand: int

    def to_dict(self) -> dict[str, object]:
        return {
            "class": self.class_name,
            "key": self.key,
            "left_field": self.left_field,
            "operator": self.operator,
            "right_field": self.right_field,
            "demand": self.demand,
        }


@dataclass(frozen=True)
class ExpressionDefinition:
    body: tuple[str, ...]

    @property
    def operation_id(self) -> str:
        return "derived-expression-" + digest(self.to_dict())[:16]

    def to_dict(self) -> dict[str, object]:
        return {"schema": DEFINITION_SCHEMA, "body": list(self.body)}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ExpressionDefinition":
        if value.get("schema") != DEFINITION_SCHEMA:
            raise ValueError("unknown M097 expression-definition schema")
        body = value.get("body")
        if not isinstance(body, list) or not body or not all(isinstance(item, str) for item in body):
            raise ValueError("malformed M097 expression body")
        if any(item not in ASSEMBLY_TOKENS for item in body):
            raise ValueError("expression body uses an instruction outside the substrate")
        if len(body) > MAX_ASSEMBLY_LENGTH:
            raise ValueError("expression body exceeds the frozen assembly bound")
        return cls(tuple(body))


@dataclass(frozen=True)
class OperationLanguageState:
    inherited_digest: str
    extensions: tuple[ExpressionDefinition, ...] = ()

    @classmethod
    def inherited(cls) -> "OperationLanguageState":
        return cls(inherited_operation_digest())

    def register(self, definition: ExpressionDefinition) -> "OperationLanguageState":
        if definition in self.extensions:
            return self
        return replace(self, extensions=self.extensions + (definition,))

    def to_dict(self) -> dict[str, object]:
        value: dict[str, object] = {
            "schema": LANGUAGE_SCHEMA,
            "inherited_digest": self.inherited_digest,
            "extensions": [item.to_dict() for item in self.extensions],
        }
        value["state_digest"] = digest(value)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "OperationLanguageState":
        recorded = value.get("state_digest")
        payload = {key: item for key, item in value.items() if key != "state_digest"}
        if recorded != digest(payload):
            raise ValueError("operation-language state digest mismatch")
        if value.get("schema") != LANGUAGE_SCHEMA:
            raise ValueError("unknown operation-language schema")
        inherited_digest = value.get("inherited_digest")
        extensions = value.get("extensions")
        if not isinstance(inherited_digest, str) or not isinstance(extensions, list):
            raise ValueError("malformed operation-language state")
        if not all(isinstance(item, dict) for item in extensions):
            raise ValueError("operation-language extensions are not closed definition records")
        if inherited_digest != inherited_operation_digest():
            raise ValueError("serialized state names another inherited operation language")
        return cls(
            inherited_digest,
            tuple(ExpressionDefinition.from_dict(item) for item in extensions),
        )


Symbol = tuple[object, ...]


def symbolic_expression(body: Sequence[str]) -> Symbol | None:
    stack: list[Symbol] = []
    for token in body:
        if token == "PUSH_LEFT":
            stack.append(("left",))
        elif token == "PUSH_RIGHT":
            stack.append(("right",))
        elif token == "NEG":
            if not stack:
                return None
            stack.append(("neg", stack.pop()))
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif token in {"ADD", "SUB", "MUL"}:
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            stack.append((token.lower(), left, right))
        else:
            return None
    return stack[0] if len(stack) == 1 else None


def evaluate_symbol(symbol: Symbol, left: int | float, right: int | float) -> int | float:
    kind = symbol[0]
    if kind == "left":
        return left
    if kind == "right":
        return right
    if kind == "neg":
        return -evaluate_symbol(symbol[1], left, right)  # type: ignore[arg-type]
    a = evaluate_symbol(symbol[1], left, right)  # type: ignore[arg-type]
    b = evaluate_symbol(symbol[2], left, right)  # type: ignore[arg-type]
    if kind == "add":
        return a + b
    if kind == "sub":
        return a - b
    if kind == "mul":
        return a * b
    raise ValueError(f"unknown symbolic expression {kind}")


def candidate_definitions() -> Iterator[ExpressionDefinition]:
    for length in range(1, MAX_ASSEMBLY_LENGTH + 1):
        for body in itertools.product(ASSEMBLY_TOKENS, repeat=length):
            yield ExpressionDefinition(tuple(body))


def inherited_operation_descriptions() -> tuple[str, ...]:
    operations = inherited.operations_for(
        "render_value_object_as_mapping",
        ("left", "right"),
        "value=left|",
    )
    return tuple(sorted(operation.describe() for operation in operations))


def inherited_operation_digest() -> str:
    return digest({
        "schema": inherited.COMPOSITION_SCHEMA,
        "bound": inherited.MAX_COMPOSITION_LENGTH,
        "operations": list(inherited_operation_descriptions()),
    })


def insufficiency_certificate(requirement: DerivedRequirement) -> dict[str, object]:
    return {
        "schema": "m097-inherited-insufficiency-v1",
        "required_expression": [
            requirement.operator, requirement.left_field, requirement.right_field
        ],
        "inherited_invariant": "every mapping value is a path from exactly one self field, optionally under one unary wrapper or zero-argument renderer call",
        "closure_argument": (
            "IncludeField and IncludeRenderedField each append one independent single-field "
            "MappingItem; NameMethod and ReturnShape add no value expression; no inherited "
            "operation combines items; rendering maps every item independently. Therefore "
            "composition depth cannot introduce ast.BinOp."
        ),
        "required_ast_node": "BinOp",
        "inherited_ast_node": "Attribute_or_unary_Call",
        "outside_constructive_image_at_any_bound": True,
        "same_language_more_budget_cannot_help": True,
        "inherited_operation_digest": inherited_operation_digest(),
    }


def _binary_operator(node: ast.operator) -> str | None:
    if isinstance(node, ast.Sub):
        return "sub"
    if isinstance(node, ast.Add):
        return "add"
    if isinstance(node, ast.Mult):
        return "mul"
    return None


def observe_requirement(root: Path, component: str) -> DerivedRequirement:
    component_path = root / component
    tree = ast.parse(component_path.read_text(encoding="utf-8"))
    classes = [item for item in tree.body if isinstance(item, ast.ClassDef)]
    class_fields = {
        item.name: {
            field.target.id
            for field in item.body
            if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name)
        }
        for item in classes
    }
    found: list[tuple[str, str, str, str, str]] = []
    for path in sorted(root.rglob("*.py")):
        if path.resolve() == component_path.resolve():
            continue
        caller = ast.parse(path.read_text(encoding="utf-8"))
        for mapping in (node for node in ast.walk(caller) if isinstance(node, ast.Dict)):
            for key, value in zip(mapping.keys, mapping.values):
                if not (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and isinstance(value, ast.BinOp)
                    and isinstance(value.left, ast.Attribute)
                    and isinstance(value.right, ast.Attribute)
                    and isinstance(value.left.value, ast.Name)
                    and isinstance(value.right.value, ast.Name)
                    and value.left.value.id == value.right.value.id
                ):
                    continue
                operator = _binary_operator(value.op)
                if operator is None:
                    continue
                candidates = [
                    name
                    for name, fields in class_fields.items()
                    if {value.left.attr, value.right.attr} <= fields
                ]
                if len(candidates) == 1:
                    found.append(
                        (candidates[0], key.value, value.left.attr, operator, value.right.attr)
                    )
    if not found:
        raise ValueError("no unambiguous binary mapping demand was observed")
    unique = set(found)
    if len(unique) != 1:
        raise ValueError("binary mapping callers disagree on the required operation")
    class_name, key, left, operator, right = unique.pop()
    return DerivedRequirement(class_name, key, left, operator, right, len(found))


@dataclass(frozen=True)
class IncludeAcquiredExpression(Operation):
    requirement: DerivedRequirement
    definition: ExpressionDefinition

    def apply(self, draft: MethodDraft) -> MethodDraft | None:
        if any(item.key == self.requirement.key for item in draft.items):
            return None
        wrapper = (
            EXTENSION_WRAPPER
            + self.definition.operation_id
            + ":"
            + self.requirement.right_field
        )
        item = MappingItem(
            self.requirement.key, self.requirement.left_field, wrapper
        )
        return replace(draft, items=draft.items + (item,))

    def describe(self) -> str:
        return "include-acquired-expression=" + self.requirement.key


def operations_for(
    requirement: DerivedRequirement,
    fields: Sequence[str],
    state: OperationLanguageState,
    taken: frozenset[str] = frozenset(),
) -> tuple[Operation, ...]:
    base = inherited.operations_for(
        "render_value_object_as_mapping", fields, "", (), taken
    )
    acquired = tuple(
        IncludeAcquiredExpression(requirement, definition)
        for definition in state.extensions
    )
    return tuple(base) + acquired


def _symbol_ast(symbol: Symbol, left_field: str, right_field: str) -> ast.expr:
    if symbol[0] == "left":
        return inherited._self_attribute(left_field)
    if symbol[0] == "right":
        return inherited._self_attribute(right_field)
    if symbol[0] == "neg":
        return ast.UnaryOp(
            op=ast.USub(), operand=_symbol_ast(symbol[1], left_field, right_field)  # type: ignore[arg-type]
        )
    operators: dict[str, ast.operator] = {
        "add": ast.Add(), "sub": ast.Sub(), "mul": ast.Mult()
    }
    return ast.BinOp(
        left=_symbol_ast(symbol[1], left_field, right_field),  # type: ignore[arg-type]
        op=operators[str(symbol[0])],
        right=_symbol_ast(symbol[2], left_field, right_field),  # type: ignore[arg-type]
    )


def render(draft: MethodDraft, state: OperationLanguageState) -> ast.FunctionDef | None:
    if not any(
        isinstance(item.wrapper, str) and item.wrapper.startswith(EXTENSION_WRAPPER)
        for item in draft.items
    ):
        return inherited.render(draft)
    if draft.name is None or draft.returns != "mapping" or not draft.items:
        return None
    definitions = {item.operation_id: item for item in state.extensions}
    values: list[ast.expr] = []
    for item in draft.items:
        wrapper = item.wrapper
        if not isinstance(wrapper, str) or not wrapper.startswith(EXTENSION_WRAPPER):
            values.append(inherited._wrapped(inherited._self_attribute(item.field), wrapper))
            continue
        operation_id, separator, right_field = wrapper[len(EXTENSION_WRAPPER):].partition(":")
        definition = definitions.get(operation_id)
        symbol = symbolic_expression(definition.body) if definition else None
        if not separator or not right_field or symbol is None:
            return None
        values.append(_symbol_ast(symbol, item.field, right_field))
    body = [
        ast.Return(
            value=ast.Dict(
                keys=[ast.Constant(value=item.key) for item in draft.items],
                values=values,
            )
        )
    ]
    return ast.FunctionDef(
        name=draft.name,
        args=ast.arguments(
            posonlyargs=[], args=[ast.arg(arg="self")], vararg=None,
            kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]
        ),
        body=body,
        decorator_list=[],
        returns=None,
        type_params=[],
    )


def method_supplies_requirement(method: ast.FunctionDef, requirement: DerivedRequirement) -> bool:
    returns = [node.value for node in ast.walk(method) if isinstance(node, ast.Return)]
    if len(returns) != 1 or not isinstance(returns[0], ast.Dict):
        return False
    mapping = returns[0]
    if len(mapping.keys) != 1 or len(mapping.values) != 1:
        return False
    key = mapping.keys[0]
    value = mapping.values[0]
    if not isinstance(key, ast.Constant) or key.value != requirement.key:
        return False
    if not (
        isinstance(value, ast.BinOp)
        and _binary_operator(value.op) == requirement.operator
        and isinstance(value.left, ast.Attribute)
        and isinstance(value.left.value, ast.Name)
        and value.left.value.id == "self"
        and value.left.attr == requirement.left_field
        and isinstance(value.right, ast.Attribute)
        and isinstance(value.right.value, ast.Name)
        and value.right.value.id == "self"
        and value.right.attr == requirement.right_field
    ):
        return False
    return True


@dataclass
class SearchResult:
    examined: int
    structural_survivors: int
    operations_offered: int
    bound: int
    methods: tuple[str, ...]
    sources: tuple[str, ...]

    @property
    def reached_structurally(self) -> bool:
        return bool(self.sources)

    def to_dict(self) -> dict[str, object]:
        return {
            "examined": self.examined,
            "structural_survivors": self.structural_survivors,
            "operations_offered": self.operations_offered,
            "bound": self.bound,
            "reached_structurally": self.reached_structurally,
            "methods": list(self.methods),
        }


def search(
    source: str,
    requirement: DerivedRequirement,
    fields: Sequence[str],
    state: OperationLanguageState,
    *,
    bound: int = inherited.MAX_COMPOSITION_LENGTH,
) -> SearchResult:
    tree = ast.parse(source)
    node = next(
        (item for item in ast.walk(tree) if isinstance(item, ast.ClassDef)
         and item.name == requirement.class_name),
        None,
    )
    if node is None:
        return SearchResult(0, 0, 0, bound, (), ())
    taken = frozenset(
        item.name for item in node.body
        if isinstance(item, ast.FunctionDef) and not item.name.startswith("_")
    )
    operations = operations_for(requirement, fields, state, taken)
    examined = 0
    survivors: list[tuple[str, str]] = []
    for chain in inherited._compositions(operations, bound):
        draft = MethodDraft()
        for operation in chain:
            grown = operation.apply(draft)
            if grown is None:
                break
            draft = grown
        else:
            function = render(draft, state)
            examined += 1
            if function is None or not method_supplies_requirement(function, requirement):
                continue
            method = inherited.unparse(function)
            modified = inherited.insert_into_class(source, requirement.class_name, method)
            if modified is not None:
                survivors.append((method, modified))
            continue
        examined += 1
    ordered = sorted(survivors, key=lambda item: digest({"method": item[0]}))
    return SearchResult(
        examined,
        len(ordered),
        len(operations),
        bound,
        tuple(item[0] for item in ordered),
        tuple(item[1] for item in ordered),
    )


__all__ = [
    "ASSEMBLY_TOKENS", "DEFINITION_SCHEMA", "DerivedRequirement",
    "ExpressionDefinition", "LANGUAGE_SCHEMA", "MAX_ASSEMBLY_LENGTH",
    "OperationLanguageState", "SearchResult", "candidate_definitions", "canonical_json",
    "digest", "evaluate_symbol", "inherited_operation_digest", "insufficiency_certificate",
    "method_supplies_requirement", "observe_requirement", "operations_for", "render", "search",
    "symbolic_expression",
]
