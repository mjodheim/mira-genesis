"""Execution-only M101 consumer capsule.

This module is copied into a two-file isolated capsule and imported by the sibling
``run.py`` entry point. It reconstructs already registered M101 definitions from
canonical lineage-state bytes, binds authored carrier atomics from public demand cases,
and executes hidden development cases. It deliberately contains no definition
assembler, acquisition transition, registration function, independent validator,
producer trigger, qualification pool, or result writer.

The shared semantics are still an authored bounded interpreter. Separating this file
from ``m101_runtime.py`` tests the narrower claim that a fresh consumer can reuse A or B
without receiving the machinery that originally assembled and registered them.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import itertools
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

STATE_SCHEMA = "m101-lineage-state-v1"
DEFINITION_SCHEMA = "m101-definition-v1"
RUNTIME_SCHEMA = "m101-fresh-executor-v1"
A_ORIGIN = "m101-a"
B_ORIGIN = "m101-b"
M100_STATE_SCHEMA = "m100-cumulative-operation-language-v1"
M100_DEFINITION_SCHEMA = "m100-cumulative-operation-v1"
M097_DEFINITION_SCHEMA = "m097-expression-operation-v1"

FORBIDDEN_A_SUBSTRINGS = (
    "text",
    "record",
    "mapping",
    "dict",
    "python",
    "syntax",
    "ast",
    "compose",
    "composition",
    "chain",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _cases(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} cases are missing")
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        case = _closed(raw, {"case_id", "input", "expected"}, f"{label} case")
        case_id = case["case_id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError(f"{label} case ids are invalid")
        seen.add(case_id)
        cases.append(copy.deepcopy(case))
    return cases


def _definition_id(origin: str, body: list[str], dependencies: list[str]) -> str:
    payload = {
        "schema": DEFINITION_SCHEMA,
        "origin": origin,
        "body": body,
        "dependencies": dependencies,
    }
    prefix = "generic-combinator" if origin == A_ORIGIN else "syntax-successor"
    return f"{prefix}-{digest(payload)[:16]}"


def _a_call_order(body: list[str]) -> tuple[int, ...] | None:
    stack: list[tuple[int, ...]] = []
    returned: tuple[int, ...] | None = None
    for token in body:
        if returned is not None:
            return None
        if token == "LOAD_INPUT":
            stack.append(())
        elif token == "APPLY_SLOT:0":
            if not stack:
                return None
            stack.append(stack.pop() + (0,))
        elif token == "APPLY_SLOT:1":
            if not stack:
                return None
            stack.append(stack.pop() + (1,))
        elif token == "DUP":
            if not stack:
                return None
            stack.append(stack[-1])
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif token == "RETURN":
            if len(stack) != 1:
                return None
            returned = stack.pop()
        else:
            return None
    return returned if returned is not None and not stack else None


def _parse_b_token(token: str) -> tuple[str, tuple[Any, ...] | None]:
    if token == "LOAD_INPUT":
        return "load", None
    if token == "RETURN":
        return "return", None
    if token.startswith("APPLY_SLOT:"):
        try:
            return "apply", (int(token.split(":", 1)[1]),)
        except ValueError:
            return "invalid", None
    if token.startswith("CALL:"):
        parts = token.split(":")
        if len(parts) != 4:
            return "invalid", None
        try:
            return "call", (parts[1], int(parts[2]), int(parts[3]))
        except ValueError:
            return "invalid", None
    return "invalid", None


def _b_call_order(body: list[str], allowed_dependency: str) -> tuple[int, ...] | None:
    loaded = False
    returned = False
    order: list[int] = []
    call_count = 0
    direct_count = 0
    call_seen = False
    for token in body:
        kind, payload = _parse_b_token(token)
        if returned:
            return None
        if kind == "load":
            if loaded:
                return None
            loaded = True
        elif kind == "call":
            if (
                not loaded
                or call_seen
                or direct_count
                or payload is None
                or len(payload) != 3
            ):
                return None
            dependency, left, right = payload
            if dependency != allowed_dependency:
                return None
            call_count += 1
            call_seen = True
            order.extend([int(left), int(right)])
        elif kind == "apply":
            if not loaded or not call_seen or payload is None:
                return None
            direct_count += 1
            if direct_count > 1:
                return None
            order.append(int(payload[0]))
        elif kind == "return":
            if not loaded:
                return None
            returned = True
        else:
            return None
    if not returned or call_count != 1 or direct_count != 1:
        return None
    return tuple(order)


def _m100_definition_id(body: list[str], dependencies: list[str], origin: str) -> str:
    if origin == "m097":
        payload = {"schema": M097_DEFINITION_SCHEMA, "body": body}
        return "derived-expression-" + digest(payload)[:16]
    payload = {
        "schema": M100_DEFINITION_SCHEMA,
        "body": body,
        "dependency_ids": dependencies,
    }
    return "cumulative-expression-" + digest(payload)[:16]


def _m100_dependencies(body: list[str]) -> list[str]:
    dependencies: list[str] = []
    for token in body:
        if token.startswith("CALL:") and token[5:] not in dependencies:
            dependencies.append(token[5:])
    return dependencies


def _m100_symbolic(
    body: list[str], signatures: dict[str, tuple[int, int]]
) -> tuple[int, int] | None:
    stack: list[tuple[int, int]] = []
    for token in body:
        if token == "PUSH_LEFT":
            stack.append((1, 0))
        elif token == "PUSH_RIGHT":
            stack.append((0, 1))
        elif token == "NEG":
            if not stack:
                return None
            left, right = stack.pop()
            stack.append((-left, -right))
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        else:
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            if token == "ADD":
                stack.append((left[0] + right[0], left[1] + right[1]))
            elif token == "SUB":
                stack.append((left[0] - right[0], left[1] - right[1]))
            elif token == "MUL":
                return None
            elif token.startswith("CALL:") and token[5:] in signatures:
                signature = signatures[token[5:]]
                stack.append(
                    (
                        signature[0] * left[0] + signature[1] * right[0],
                        signature[0] * left[1] + signature[1] * right[1],
                    )
                )
            else:
                return None
    return stack[0] if len(stack) == 1 else None


def decode_m100_state(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"embedded M100 state is not canonical ASCII JSON: {error}") from error
    if canonical_json(value).encode("ascii") != raw:
        raise ValueError("embedded M100 state bytes are not canonical JSON")
    value = _closed(
        value,
        {
            "schema",
            "inherited_digest",
            "origin_m097_state_digest",
            "operations",
            "state_digest",
        },
        "embedded M100 state",
    )
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    if value["state_digest"] != digest(payload) or value["schema"] != M100_STATE_SCHEMA:
        raise ValueError("embedded M100 state binding is invalid")
    operations = value["operations"]
    if not isinstance(operations, list) or len(operations) != 3:
        raise ValueError("embedded M100 state is not the complete S3 lineage")
    signatures: dict[str, tuple[int, int]] = {}
    for index, raw_definition in enumerate(operations):
        definition = _closed(
            raw_definition,
            {"schema", "operation_id", "origin", "body", "dependency_ids"},
            "embedded M100 operation",
        )
        operation_id = definition["operation_id"]
        origin = definition["origin"]
        body = definition["body"]
        dependencies = definition["dependency_ids"]
        if definition["schema"] != M100_DEFINITION_SCHEMA:
            raise ValueError("embedded M100 operation schema mismatch")
        if not isinstance(operation_id, str) or origin not in {"m097", "m100-cycle"}:
            raise ValueError("embedded M100 operation identity is invalid")
        if not isinstance(body, list) or not 0 < len(body) <= 6 or not all(
            isinstance(token, str) for token in body
        ):
            raise ValueError("embedded M100 operation body is invalid")
        if not isinstance(dependencies, list) or not all(
            isinstance(dependency, str) for dependency in dependencies
        ):
            raise ValueError("embedded M100 dependencies are invalid")
        if dependencies != _m100_dependencies(body):
            raise ValueError("embedded M100 live dependencies changed")
        if operation_id != _m100_definition_id(body, dependencies, str(origin)):
            raise ValueError("embedded M100 operation address changed")
        if any(dependency not in signatures for dependency in dependencies):
            raise ValueError("embedded M100 operation has a missing dependency")
        if index == 0:
            if origin != "m097" or dependencies:
                raise ValueError("embedded M100 A origin changed")
        elif origin != "m100-cycle":
            raise ValueError("embedded M100 successor origin changed")
        signature = _m100_symbolic(body, signatures)
        if signature is None:
            raise ValueError("embedded M100 operation is not executable affine state")
        signatures[operation_id] = signature
    if list(signatures.values()) != [(1, -1), (1, 1), (1, 2)]:
        raise ValueError("embedded M100 A/B/C semantics changed")
    return value


def decode_state(raw: bytes) -> dict[str, Any]:
    try:
        decoded = raw.decode("ascii")
        value = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"M101 state is not canonical ASCII JSON: {error}") from error
    if canonical_json(value).encode("ascii") != raw:
        raise ValueError("M101 state bytes are not canonical JSON")
    value = _closed(
        value,
        {"schema", "m100_sha256", "m100_ascii", "definitions", "state_digest"},
        "M101 state",
    )
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    if value["state_digest"] != digest(payload):
        raise ValueError("M101 state digest mismatch")
    if value["schema"] != STATE_SCHEMA:
        raise ValueError("M101 state schema mismatch")
    if not isinstance(value["m100_ascii"], str) or not isinstance(value["m100_sha256"], str):
        raise ValueError("M101 predecessor binding is invalid")
    if sha256_bytes(value["m100_ascii"].encode("ascii")) != value["m100_sha256"]:
        raise ValueError("M100 predecessor bytes changed")
    decode_m100_state(value["m100_ascii"].encode("ascii"))
    definitions = value["definitions"]
    if not isinstance(definitions, list) or len(definitions) > 2:
        raise ValueError("M101 definition census is invalid")

    seen: dict[str, dict[str, Any]] = {}
    a_id: str | None = None
    for index, raw_definition in enumerate(definitions):
        item = _closed(
            raw_definition,
            {"schema", "definition_id", "origin", "body", "dependencies"},
            "M101 definition",
        )
        if item["schema"] != DEFINITION_SCHEMA:
            raise ValueError("M101 definition schema mismatch")
        if item["origin"] not in {A_ORIGIN, B_ORIGIN}:
            raise ValueError("M101 definition origin is invalid")
        if not isinstance(item["body"], list) or not all(
            isinstance(token, str) for token in item["body"]
        ):
            raise ValueError("M101 definition body is invalid")
        if not isinstance(item["dependencies"], list) or not all(
            isinstance(dependency, str) for dependency in item["dependencies"]
        ):
            raise ValueError("M101 dependency list is invalid")
        if item["definition_id"] != _definition_id(
            str(item["origin"]), list(item["body"]), list(item["dependencies"])
        ):
            raise ValueError("M101 content-addressed definition id mismatch")
        if any(dependency not in seen for dependency in item["dependencies"]):
            raise ValueError("M101 definition has a missing or forward dependency")
        if item["definition_id"] in seen:
            raise ValueError("duplicate M101 definition")

        if index == 0:
            if item["origin"] != A_ORIGIN or item["dependencies"]:
                raise ValueError("the first M101 definition must be dependency-free A")
            order = _a_call_order(list(item["body"]))
            if order is None or len(order) != 2 or any(slot not in {0, 1} for slot in order):
                raise ValueError("A is not a well-formed generic two-stage combinator")
            text = canonical_json(item).lower()
            if any(term in text for term in FORBIDDEN_A_SUBSTRINGS):
                raise ValueError("A contains a forbidden carrier or shortcut identifier")
            a_id = str(item["definition_id"])
        else:
            if item["origin"] != B_ORIGIN or a_id is None:
                raise ValueError("only B may follow A")
            if item["dependencies"] != [a_id]:
                raise ValueError("B does not retain exactly one live A dependency")
            if _b_call_order(list(item["body"]), a_id) != (0, 1, 2):
                raise ValueError("B does not encode the required three-effect order through A")
        seen[str(item["definition_id"])] = item
    return value


@dataclass(frozen=True)
class Atomic:
    descriptor: dict[str, Any]
    apply: Callable[[Any], Any]

    @property
    def identity(self) -> str:
        return digest(self.descriptor)


def _require_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("text atomic received a non-string")
    return value


def _text_atomic(descriptor: dict[str, Any]) -> Atomic:
    kind = descriptor.get("kind")
    if kind == "strip":
        return Atomic(descriptor, lambda value: _require_text(value).strip())
    if kind == "upper":
        return Atomic(descriptor, lambda value: _require_text(value).upper())
    if kind == "lower":
        return Atomic(descriptor, lambda value: _require_text(value).lower())
    if kind == "prefix" and isinstance(descriptor.get("value"), str):
        prefix = descriptor["value"]
        return Atomic(descriptor, lambda value: prefix + _require_text(value))
    if kind == "suffix" and isinstance(descriptor.get("value"), str):
        suffix = descriptor["value"]
        return Atomic(descriptor, lambda value: _require_text(value) + suffix)
    if kind == "replace" and isinstance(descriptor.get("old"), str) and isinstance(
        descriptor.get("new"), str
    ):
        old, new = descriptor["old"], descriptor["new"]
        return Atomic(descriptor, lambda value: _require_text(value).replace(old, new))
    raise ValueError("unknown text atomic descriptor")


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("record atomic received a non-mapping")
    return copy.deepcopy(value)


def _record_atomic(descriptor: dict[str, Any]) -> Atomic:
    kind = descriptor.get("kind")
    if kind == "rename_key" and isinstance(descriptor.get("old"), str) and isinstance(
        descriptor.get("new"), str
    ):
        old, new = descriptor["old"], descriptor["new"]

        def rename(value: Any) -> Any:
            out = _mapping(value)
            if old in out:
                out[new] = out.pop(old)
            return out

        return Atomic(descriptor, rename)
    if kind == "drop_key" and isinstance(descriptor.get("key"), str):
        key = descriptor["key"]

        def drop(value: Any) -> Any:
            out = _mapping(value)
            out.pop(key, None)
            return out

        return Atomic(descriptor, drop)
    if kind == "sort_list" and isinstance(descriptor.get("key"), str):
        key = descriptor["key"]

        def sort_list(value: Any) -> Any:
            out = _mapping(value)
            if key in out:
                if not isinstance(out[key], list):
                    raise ValueError("sort_list target is not a list")
                out[key] = sorted(out[key])
            return out

        return Atomic(descriptor, sort_list)
    if kind == "set_default" and isinstance(descriptor.get("key"), str):
        key = descriptor["key"]
        default = copy.deepcopy(descriptor.get("value"))

        def set_default(value: Any) -> Any:
            out = _mapping(value)
            out.setdefault(key, copy.deepcopy(default))
            return out

        return Atomic(descriptor, set_default)
    raise ValueError("unknown record atomic descriptor")


def _rename_name_in_function(function: ast.FunctionDef, old: str, new: str) -> None:
    class Rename(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id == old:
                node.id = new
            return node

    Rename().visit(function)


def _syntax_transform(source: Any, transformer: ast.NodeTransformer) -> str:
    if not isinstance(source, str):
        raise ValueError("syntax atomic received non-source")
    tree = ast.parse(source)
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _syntax_atomic(descriptor: dict[str, Any]) -> Atomic:
    kind = descriptor.get("kind")
    if kind == "rename_function" and isinstance(descriptor.get("old"), str) and isinstance(
        descriptor.get("new"), str
    ):
        old, new = descriptor["old"], descriptor["new"]

        class Transform(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
                self.generic_visit(node)
                if node.name == old:
                    node.name = new
                return node

        return Atomic(descriptor, lambda value: _syntax_transform(value, Transform()))
    if (
        kind == "rename_argument"
        and isinstance(descriptor.get("function"), str)
        and isinstance(descriptor.get("old"), str)
        and isinstance(descriptor.get("new"), str)
    ):
        function_name, old, new = descriptor["function"], descriptor["old"], descriptor["new"]

        class Transform(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
                self.generic_visit(node)
                if node.name == function_name:
                    changed = False
                    for argument in node.args.args:
                        if argument.arg == old:
                            argument.arg = new
                            changed = True
                    if changed:
                        _rename_name_in_function(node, old, new)
                return node

        return Atomic(descriptor, lambda value: _syntax_transform(value, Transform()))
    if kind == "wrap_return" and descriptor.get("call") in {"abs", "str", "repr"}:
        call_name = str(descriptor["call"])

        class Transform(ast.NodeTransformer):
            def visit_Return(self, node: ast.Return) -> ast.AST:
                self.generic_visit(node)
                if node.value is not None:
                    node.value = ast.Call(
                        func=ast.Name(id=call_name, ctx=ast.Load()),
                        args=[node.value],
                        keywords=[],
                    )
                return node

        return Atomic(descriptor, lambda value: _syntax_transform(value, Transform()))
    if kind == "add_docstring" and isinstance(descriptor.get("text"), str):
        document = descriptor["text"]

        class Transform(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
                self.generic_visit(node)
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    node.body.insert(0, ast.Expr(value=ast.Constant(value=document)))
                return node

        return Atomic(descriptor, lambda value: _syntax_transform(value, Transform()))
    raise ValueError("unknown syntax atomic descriptor")


def atomic_from_descriptor(carrier: str, descriptor: dict[str, Any]) -> Atomic:
    if not isinstance(descriptor, dict) or not isinstance(descriptor.get("kind"), str):
        raise ValueError("atomic descriptor is invalid")
    if carrier == "text":
        return _text_atomic(copy.deepcopy(descriptor))
    if carrier == "record":
        return _record_atomic(copy.deepcopy(descriptor))
    if carrier == "syntax":
        return _syntax_atomic(copy.deepcopy(descriptor))
    raise ValueError("unknown carrier")


def _world(raw: Any) -> dict[str, Any]:
    value = _closed(
        raw,
        {"id", "role", "carrier", "catalog", "public_cases", "hidden_cases"},
        "M101 execution world",
    )
    if not isinstance(value["id"], str) or not value["id"]:
        raise ValueError("world id is invalid")
    if not isinstance(value["role"], str) or not value["role"]:
        raise ValueError("world role is invalid")
    if value["carrier"] not in {"text", "record", "syntax"}:
        raise ValueError("world carrier is invalid")
    if not isinstance(value["catalog"], list) or not value["catalog"]:
        raise ValueError("world catalog is invalid")
    value["public_cases"] = _cases(value["public_cases"], "world public")
    value["hidden_cases"] = _cases(value["hidden_cases"], "world hidden")
    public_ids = {case["case_id"] for case in value["public_cases"]}
    hidden_ids = {case["case_id"] for case in value["hidden_cases"]}
    if public_ids & hidden_ids:
        raise ValueError("public and hidden case ids overlap")
    return value


def _m100_world(raw: Any) -> dict[str, Any]:
    value = _closed(
        raw,
        {"id", "role", "carrier", "operation_index", "public_cases", "hidden_cases"},
        "M101 M100-conservation world",
    )
    if not isinstance(value["id"], str) or not value["id"]:
        raise ValueError("M100-conservation world id is invalid")
    if value["role"] != "m100_conservation" or value["carrier"] != "m100":
        raise ValueError("M100-conservation world role is invalid")
    if value["operation_index"] not in {0, 1, 2}:
        raise ValueError("M100-conservation operation index is invalid")
    value["public_cases"] = _cases(value["public_cases"], "M100 world public")
    value["hidden_cases"] = _cases(value["hidden_cases"], "M100 world hidden")
    public_ids = {case["case_id"] for case in value["public_cases"]}
    hidden_ids = {case["case_id"] for case in value["hidden_cases"]}
    if public_ids & hidden_ids:
        raise ValueError("M100 world public and hidden case ids overlap")
    for case in value["public_cases"] + value["hidden_cases"]:
        arguments = _closed(case["input"], {"left", "right"}, "M100 case input")
        if any(
            isinstance(arguments[key], bool) or not isinstance(arguments[key], (int, float))
            for key in ("left", "right")
        ):
            raise ValueError("M100 case input is not numeric")
        if isinstance(case["expected"], bool) or not isinstance(case["expected"], (int, float)):
            raise ValueError("M100 case expectation is not numeric")
    return value


def build_catalog(world: dict[str, Any]) -> list[Atomic]:
    atomics = [
        atomic_from_descriptor(str(world["carrier"]), descriptor)
        for descriptor in world["catalog"]
    ]
    if len({atomic.identity for atomic in atomics}) != len(atomics):
        raise ValueError("world contains duplicate atomic descriptors")
    return atomics


def _execute_t0_baseline(world: dict[str, Any], catalog: list[Atomic]) -> dict[str, Any]:
    """Evaluate T0's complete one-atomic image under a matched N-squared budget.

    This function and retained-A execution live in the same frozen executor and receive
    the same world payload.  The state is the only arm input that differs.  Repeating
    the N single-atomic candidates spends the matched budget but cannot compose them.
    """
    candidate_budget = len(catalog) ** 2
    accepted: list[int] = []
    for attempt in range(candidate_budget):
        index = attempt % len(catalog)
        atomic = catalog[index]
        try:
            if all(
                atomic.apply(copy.deepcopy(case["input"])) == case["expected"]
                for case in world["public_cases"]
            ):
                accepted.append(index)
        except Exception:
            continue
    unique = sorted(set(accepted), key=lambda index: catalog[index].identity)
    selected = unique[0] if unique else None
    outcomes = []
    if selected is not None:
        for case in world["hidden_cases"]:
            try:
                output = catalog[selected].apply(copy.deepcopy(case["input"]))
                passed = output == case["expected"]
            except Exception as error:
                output = {"error": f"{type(error).__name__}: {error}"}
                passed = False
            outcomes.append({"case_id": case["case_id"], "passed": passed, "output": output})
    reachable = bool(outcomes) and all(item["passed"] for item in outcomes)
    return {
        "schema": "m101-t0-baseline-execution-v1",
        "confirmed": not reachable,
        "reachable": reachable,
        "public_case_ids": [case["case_id"] for case in world["public_cases"]],
        "hidden_case_ids": [case["case_id"] for case in world["hidden_cases"]],
        "selected_atomic_index": selected,
        "candidate_budget": candidate_budget,
        "search": {
            "assembled": candidate_budget,
            "accepted": len(accepted),
            "unique_semantic_candidates": len(catalog),
            "repeated_budget_rounds": candidate_budget // len(catalog),
        },
        "structural_max_atomic_effects": 1,
        "more_budget_same_language_can_exceed_one_effect": False,
        "hidden_passed": sum(bool(item["passed"]) for item in outcomes),
        "hidden_total": len(world["hidden_cases"]),
        "outcomes": outcomes,
    }


def _execute_a_body(body: list[str], value: Any, slots: tuple[Atomic, Atomic]) -> Any | None:
    stack: list[Any] = []
    returned = False
    result: Any = None
    for token in body:
        if returned:
            return None
        if token == "LOAD_INPUT":
            stack.append(copy.deepcopy(value))
        elif token == "APPLY_SLOT:0":
            if not stack:
                return None
            stack.append(slots[0].apply(stack.pop()))
        elif token == "APPLY_SLOT:1":
            if not stack:
                return None
            stack.append(slots[1].apply(stack.pop()))
        elif token == "DUP":
            if not stack:
                return None
            stack.append(copy.deepcopy(stack[-1]))
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif token == "RETURN":
            if len(stack) != 1:
                return None
            result = stack.pop()
            returned = True
        else:
            return None
    return result if returned and not stack else None


def _a_bindings(
    body: list[str], public_cases: list[dict[str, Any]], catalog: list[Atomic]
) -> tuple[list[int] | None, dict[str, Any]]:
    """Resolve carrier bindings only by interpreting the registered A bytes."""
    accepted: list[tuple[int, int]] = []
    assembled = 0
    for left, right in itertools.product(range(len(catalog)), repeat=2):
        assembled += 1
        slots = (catalog[left], catalog[right])
        try:
            if all(
                _execute_a_body(body, case["input"], slots) == case["expected"]
                for case in public_cases
            ):
                accepted.append((left, right))
        except Exception:
            continue
    accepted.sort(
        key=lambda item: digest([catalog[item[0]].descriptor, catalog[item[1]].descriptor])
    )
    selected = list(accepted[0]) if accepted else None
    report: dict[str, Any] = {"assembled": assembled, "accepted": len(accepted)}
    if selected is not None:
        report["selected_binding_digest"] = digest(
            [catalog[selected[0]].descriptor, catalog[selected[1]].descriptor]
        )
    return selected, report


def _execute_b_body(
    body: list[str], state: dict[str, Any], value: Any, slots: tuple[Atomic, Atomic, Atomic]
) -> Any | None:
    a = state["definitions"][0] if state["definitions"] else None
    current: Any = None
    loaded = False
    returned = False
    for token in body:
        kind, payload = _parse_b_token(token)
        if returned:
            return None
        if kind == "load":
            if loaded:
                return None
            current = copy.deepcopy(value)
            loaded = True
        elif kind == "call":
            if not loaded or a is None or payload is None or len(payload) != 3:
                return None
            dependency, left, right = payload
            if dependency != a["definition_id"]:
                return None
            current = _execute_a_body(
                list(a["body"]), current, (slots[int(left)], slots[int(right)])
            )
            if current is None:
                return None
        elif kind == "apply":
            if not loaded or payload is None:
                return None
            index = int(payload[0])
            if index not in {0, 1, 2}:
                return None
            current = slots[index].apply(current)
        elif kind == "return":
            if not loaded:
                return None
            returned = True
        else:
            return None
    return current if returned else None


def _b_bindings(
    body: list[str],
    state: dict[str, Any],
    public_cases: list[dict[str, Any]],
    catalog: list[Atomic],
) -> tuple[list[int] | None, dict[str, Any]]:
    """Resolve carrier bindings only through registered B and its live A call."""
    accepted: list[tuple[int, int, int]] = []
    assembled = 0
    for first, second, third in itertools.product(range(len(catalog)), repeat=3):
        assembled += 1
        slots = (catalog[first], catalog[second], catalog[third])
        try:
            if all(
                _execute_b_body(body, state, case["input"], slots) == case["expected"]
                for case in public_cases
            ):
                accepted.append((first, second, third))
        except Exception:
            continue
    accepted.sort(
        key=lambda item: digest(
            [
                catalog[item[0]].descriptor,
                catalog[item[1]].descriptor,
                catalog[item[2]].descriptor,
            ]
        )
    )
    selected = list(accepted[0]) if accepted else None
    report: dict[str, Any] = {"assembled": assembled, "accepted": len(accepted)}
    if selected is not None:
        report["selected_binding_digest"] = digest(
            [catalog[selected[0]].descriptor, catalog[selected[1]].descriptor, catalog[selected[2]].descriptor]
        )
    return selected, report


def _execute_m100_body(
    body: list[str],
    definitions: dict[str, dict[str, Any]],
    left: int | float,
    right: int | float,
) -> int | float | None:
    stack: list[int | float] = []
    for token in body:
        if token == "PUSH_LEFT":
            stack.append(left)
        elif token == "PUSH_RIGHT":
            stack.append(right)
        elif token == "NEG":
            if not stack:
                return None
            stack.append(-stack.pop())
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        else:
            if len(stack) < 2:
                return None
            call_right = stack.pop()
            call_left = stack.pop()
            if token == "ADD":
                stack.append(call_left + call_right)
            elif token == "SUB":
                stack.append(call_left - call_right)
            elif token == "MUL":
                stack.append(call_left * call_right)
            elif token.startswith("CALL:") and token[5:] in definitions:
                target = definitions[token[5:]]
                result = _execute_m100_body(
                    list(target["body"]), definitions, call_left, call_right
                )
                if result is None:
                    return None
                stack.append(result)
            else:
                return None
    return stack[0] if len(stack) == 1 else None


def execute_a(state: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    catalog = build_catalog(world)
    if not state["definitions"]:
        return _execute_t0_baseline(world, catalog)
    a = state["definitions"][0]
    inferred, binding_search = _a_bindings(
        list(a["body"]), world["public_cases"], catalog
    )
    if inferred is None:
        return {
            "schema": "m101-a-execution-v1",
            "confirmed": False,
            "binding_search": binding_search,
            "hidden_passed": 0,
            "hidden_total": len(world["hidden_cases"]),
        }
    slots = (catalog[inferred[0]], catalog[inferred[1]])
    outcomes = []
    for case in world["hidden_cases"]:
        try:
            output = _execute_a_body(list(a["body"]), case["input"], slots)
            passed = output == case["expected"]
        except Exception as error:
            output = {"error": f"{type(error).__name__}: {error}"}
            passed = False
        outcomes.append({"case_id": case["case_id"], "passed": passed, "output": output})
    return {
        "schema": "m101-a-execution-v1",
        "confirmed": all(item["passed"] for item in outcomes),
        "public_case_ids": [case["case_id"] for case in world["public_cases"]],
        "hidden_case_ids": [case["case_id"] for case in world["hidden_cases"]],
        "inferred_slot_indices": inferred,
        "binding_search": binding_search,
        "hidden_passed": sum(bool(item["passed"]) for item in outcomes),
        "hidden_total": len(outcomes),
        "outcomes": outcomes,
    }


def execute_b(state: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    if len(state["definitions"]) != 2:
        raise ValueError("B is not registered")
    a, b = state["definitions"]
    if b["dependencies"] != [a["definition_id"]]:
        raise ValueError("B lost its live A dependency")
    catalog = build_catalog(world)
    inferred, binding_search = _b_bindings(
        list(b["body"]), state, world["public_cases"], catalog
    )
    if inferred is None:
        return {
            "schema": "m101-b-execution-v1",
            "confirmed": False,
            "binding_search": binding_search,
            "hidden_passed": 0,
            "hidden_total": len(world["hidden_cases"]),
        }
    slots = (catalog[inferred[0]], catalog[inferred[1]], catalog[inferred[2]])
    outcomes = []
    for case in world["hidden_cases"]:
        try:
            output = _execute_b_body(list(b["body"]), state, case["input"], slots)
            passed = output == case["expected"]
        except Exception as error:
            output = {"error": f"{type(error).__name__}: {error}"}
            passed = False
        outcomes.append({"case_id": case["case_id"], "passed": passed, "output": output})
    return {
        "schema": "m101-b-execution-v1",
        "confirmed": all(item["passed"] for item in outcomes),
        "public_case_ids": [case["case_id"] for case in world["public_cases"]],
        "hidden_case_ids": [case["case_id"] for case in world["hidden_cases"]],
        "inferred_slot_indices": inferred,
        "binding_search": binding_search,
        "hidden_passed": sum(bool(item["passed"]) for item in outcomes),
        "hidden_total": len(outcomes),
        "outcomes": outcomes,
    }


def execute_m100(state: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    predecessor = decode_m100_state(state["m100_ascii"].encode("ascii"))
    definitions = {
        str(item["operation_id"]): item for item in predecessor["operations"]
    }
    operation = predecessor["operations"][int(world["operation_index"])]
    outcomes = []
    for case in world["hidden_cases"]:
        arguments = case["input"]
        try:
            output = _execute_m100_body(
                list(operation["body"]), definitions, arguments["left"], arguments["right"]
            )
            passed = output == case["expected"]
        except Exception as error:
            output = {"error": f"{type(error).__name__}: {error}"}
            passed = False
        outcomes.append({"case_id": case["case_id"], "passed": passed, "output": output})
    return {
        "schema": "m101-m100-conservation-execution-v1",
        "confirmed": all(item["passed"] for item in outcomes),
        "operation_index": world["operation_index"],
        "operation_id": operation["operation_id"],
        "public_case_ids": [case["case_id"] for case in world["public_cases"]],
        "hidden_case_ids": [case["case_id"] for case in world["hidden_cases"]],
        "hidden_passed": sum(bool(item["passed"]) for item in outcomes),
        "hidden_total": len(outcomes),
        "outcomes": outcomes,
    }


def _project_modules() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if name.startswith(("metamorphosis", "scripts", "mira_core"))
    )


def run(action: str, state_path: Path, world_path: Path) -> dict[str, Any]:
    raw = state_path.read_bytes()
    state = decode_state(raw)
    world_raw = world_path.read_bytes()
    try:
        world_value = json.loads(world_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"world is not JSON: {error}") from error
    world = _m100_world(world_value) if action == "execute-m100" else _world(world_value)
    if action == "execute-a":
        execution = execute_a(state, world)
    elif action == "execute-b":
        execution = execute_b(state, world)
    elif action == "execute-m100":
        execution = execute_m100(state, world)
    else:
        raise ValueError("unknown M101 execution action")
    return {
        "schema": RUNTIME_SCHEMA,
        "action": action,
        "pid": os.getpid(),
        "isolated_mode": sys.flags.isolated == 1,
        "state_raw_sha256": sha256_bytes(raw),
        "world_raw_sha256": sha256_bytes(world_raw),
        "state_digest": state["state_digest"],
        "m100_sha256": state["m100_sha256"],
        "definition_count": len(state["definitions"]),
        "confirmed": execution["confirmed"],
        "execution": execution,
        "imported_project_modules": _project_modules(),
        "search_path": [str(item) for item in sys.path],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("execute-a", "execute-b", "execute-m100"))
    parser.add_argument("--state", required=True)
    parser.add_argument("--world", required=True)
    arguments = parser.parse_args()
    try:
        result = run(arguments.action, Path(arguments.state), Path(arguments.world))
    except Exception as error:
        print(
            json.dumps(
                {
                    "schema": RUNTIME_SCHEMA,
                    "action": arguments.action,
                    "pid": os.getpid(),
                    "isolated_mode": sys.flags.isolated == 1,
                    "confirmed": False,
                    "failed_closed": True,
                    "error": f"{type(error).__name__}: {error}",
                    "imported_project_modules": _project_modules(),
                    "search_path": [str(item) for item in sys.path],
                },
                sort_keys=True,
            )
        )
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0 if result["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
