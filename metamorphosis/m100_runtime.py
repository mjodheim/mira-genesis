"""Standalone cumulative-operation runtime for M100.

The qualification runner copies this file and a minimal entry point into an isolated
directory.  The capsule deliberately imports no project module.  It can migrate the
single M097-acquired operation, acquire a bounded successor only through calls to
already registered operations, validate persisted state, and execute a selected live
operation against fresh Python source.

This is a bounded constructive-language experiment.  It is not an unrestricted code
generator, a self-hosting runtime, or evidence of open-ended improvement.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import itertools
import json
import os
import sys
import types
from pathlib import Path

M097_LANGUAGE_SCHEMA = "m097-operation-language-v1"
M097_DEFINITION_SCHEMA = "m097-expression-operation-v1"
STATE_SCHEMA = "m100-cumulative-operation-language-v1"
DEFINITION_SCHEMA = "m100-cumulative-operation-v1"
RUNTIME_SCHEMA = "m100-isolated-runtime-v1"

STATIC_TOKENS = ("PUSH_LEFT", "PUSH_RIGHT", "NEG", "SWAP")
LEGACY_TOKENS = {"PUSH_LEFT", "PUSH_RIGHT", "ADD", "SUB", "MUL", "NEG", "SWAP"}
MAX_BODY = 6


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _closed(value: object, keys: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _definition_id(body: list[str], dependency_ids: list[str], origin: str) -> str:
    if origin == "m097":
        original = {"schema": M097_DEFINITION_SCHEMA, "body": body}
        return "derived-expression-" + digest(original)[:16]
    payload = {
        "schema": DEFINITION_SCHEMA,
        "body": body,
        "dependency_ids": dependency_ids,
    }
    return "cumulative-expression-" + digest(payload)[:16]


def _dependency_ids(body: list[str]) -> list[str]:
    found: list[str] = []
    for token in body:
        if token.startswith("CALL:"):
            operation_id = token[5:]
            if operation_id and operation_id not in found:
                found.append(operation_id)
    return found


def _definition(
    body: list[str], dependency_ids: list[str], origin: str
) -> dict[str, object]:
    return {
        "schema": DEFINITION_SCHEMA,
        "operation_id": _definition_id(body, dependency_ids, origin),
        "origin": origin,
        "body": body,
        "dependency_ids": dependency_ids,
    }


def _state(
    inherited_digest: str,
    origin_m097_state_digest: str,
    operations: list[dict[str, object]],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": STATE_SCHEMA,
        "inherited_digest": inherited_digest,
        "origin_m097_state_digest": origin_m097_state_digest,
        "operations": operations,
    }
    payload["state_digest"] = digest(payload)
    return payload


def _decode_ascii_json(raw: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not canonical ASCII JSON: {error}") from error
    if raw != canonical_json(value).encode("ascii"):
        raise ValueError(f"{label} bytes are not canonical JSON")
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not an object")
    return value


def decode_m097_state(raw: bytes) -> dict[str, object]:
    value = _closed(
        _decode_ascii_json(raw, "M097 state"),
        {"schema", "inherited_digest", "extensions", "state_digest"},
        "M097 state",
    )
    recorded = value["state_digest"]
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    if recorded != digest(payload):
        raise ValueError("M097 state digest mismatch")
    if value["schema"] != M097_LANGUAGE_SCHEMA:
        raise ValueError("M097 state schema mismatch")
    if not isinstance(value["inherited_digest"], str):
        raise ValueError("M097 inherited digest is invalid")
    extensions = value["extensions"]
    if not isinstance(extensions, list) or len(extensions) > 1:
        raise ValueError("M100 migration accepts only the M097 pre/post-acquisition states")
    if not extensions:
        return value
    item = _closed(extensions[0], {"schema", "body"}, "M097 definition")
    body = item["body"]
    if item["schema"] != M097_DEFINITION_SCHEMA:
        raise ValueError("M097 definition schema mismatch")
    if not isinstance(body, list) or not 0 < len(body) <= MAX_BODY:
        raise ValueError("M097 definition body is invalid")
    if not all(isinstance(token, str) and token in LEGACY_TOKENS for token in body):
        raise ValueError("M097 definition contains an unknown token")
    if _symbolic_program(body, {}) is None:
        raise ValueError("M097 definition is not a complete affine binary operation")
    return value


def migrate_m097_state(raw: bytes) -> dict[str, object]:
    source = decode_m097_state(raw)
    operations = []
    if source["extensions"]:
        body = list(source["extensions"][0]["body"])
        operations.append(_definition(body, [], "m097"))
    return _state(
        str(source["inherited_digest"]), str(source["state_digest"]), operations
    )


def _scale(pair: tuple[int, int], coefficient: int) -> tuple[int, int]:
    return pair[0] * coefficient, pair[1] * coefficient


def _add(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    return left[0] + right[0], left[1] + right[1]


def _apply_signature(
    signature: tuple[int, int],
    left: tuple[int, int],
    right: tuple[int, int],
) -> tuple[int, int]:
    return _add(_scale(left, signature[0]), _scale(right, signature[1]))


def _symbolic_program(
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
            stack.append(_scale(stack.pop(), -1))
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
                stack.append(_add(left, right))
            elif token == "SUB":
                stack.append(_add(left, _scale(right, -1)))
            elif token == "MUL":
                return None
            elif token.startswith("CALL:") and token[5:] in signatures:
                stack.append(_apply_signature(signatures[token[5:]], left, right))
            else:
                return None
    return stack[0] if len(stack) == 1 else None


def decode_state(raw: bytes) -> dict[str, object]:
    value = _closed(
        _decode_ascii_json(raw, "M100 state"),
        {
            "schema", "inherited_digest", "origin_m097_state_digest",
            "operations", "state_digest",
        },
        "M100 state",
    )
    recorded = value["state_digest"]
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    if recorded != digest(payload):
        raise ValueError("M100 state digest mismatch")
    if value["schema"] != STATE_SCHEMA:
        raise ValueError("M100 state schema mismatch")
    if not isinstance(value["inherited_digest"], str) or not isinstance(
        value["origin_m097_state_digest"], str
    ):
        raise ValueError("M100 predecessor digests are invalid")
    operations = value["operations"]
    if not isinstance(operations, list):
        raise ValueError("M100 operations are not a list")

    signatures: dict[str, tuple[int, int]] = {}
    for index, raw_definition in enumerate(operations):
        definition = _closed(
            raw_definition,
            {"schema", "operation_id", "origin", "body", "dependency_ids"},
            "M100 operation",
        )
        if definition["schema"] != DEFINITION_SCHEMA:
            raise ValueError("M100 operation schema mismatch")
        operation_id = definition["operation_id"]
        origin = definition["origin"]
        body = definition["body"]
        dependencies = definition["dependency_ids"]
        if not isinstance(operation_id, str) or not isinstance(origin, str):
            raise ValueError("M100 operation identity is invalid")
        if origin not in {"m097", "m100-cycle"}:
            raise ValueError("M100 operation origin is invalid")
        if not isinstance(body, list) or not 0 < len(body) <= MAX_BODY:
            raise ValueError("M100 operation body is invalid")
        if not all(isinstance(token, str) for token in body):
            raise ValueError("M100 operation token is invalid")
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            raise ValueError("M100 operation dependency list is invalid")
        if dependencies != _dependency_ids(body):
            raise ValueError("M100 operation dependencies do not match live calls")
        if operation_id != _definition_id(body, dependencies, origin):
            raise ValueError("M100 operation identifier mismatch")
        if operation_id in signatures:
            raise ValueError("duplicate M100 operation identifier")
        if index == 0:
            if origin != "m097" or dependencies:
                raise ValueError("the first M100 operation is not the M097 acquisition")
            if not all(token in LEGACY_TOKENS for token in body):
                raise ValueError("migrated M097 operation uses an unknown token")
        else:
            if origin != "m100-cycle":
                raise ValueError("only the first operation may originate in M097")
            if any(
                token not in STATIC_TOKENS
                and not (token.startswith("CALL:") and token[5:] in signatures)
                for token in body
            ):
                raise ValueError("new operation bypasses prior registered operations")
        if any(dependency not in signatures for dependency in dependencies):
            raise ValueError("M100 operation has a missing or forward dependency")
        signature = _symbolic_program(body, signatures)
        if signature is None:
            raise ValueError("M100 operation is not a complete affine program")
        signatures[operation_id] = signature
    return value


def encode_state(state: dict[str, object]) -> bytes:
    checked = decode_state(canonical_json(state).encode("ascii"))
    return canonical_json(checked).encode("ascii")


def operation_signatures(state: dict[str, object]) -> dict[str, tuple[int, int]]:
    checked = decode_state(canonical_json(state).encode("ascii"))
    signatures: dict[str, tuple[int, int]] = {}
    for definition in checked["operations"]:
        signatures[str(definition["operation_id"])] = _symbolic_program(
            list(definition["body"]), signatures
        )
    return signatures


def acquire(
    state: dict[str, object],
    target: tuple[int, int],
    bound: int,
    public_cases: list[tuple[int | float, int | float]] | None = None,
    *,
    register: bool,
) -> dict[str, object]:
    checked = decode_state(canonical_json(state).encode("ascii"))
    if not 1 <= bound <= MAX_BODY:
        raise ValueError("acquisition bound is outside the runtime limit")
    signatures = operation_signatures(checked)
    alphabet = list(STATIC_TOKENS) + [f"CALL:{item}" for item in signatures]
    cases = public_cases or [(0, 0), (1, 0), (0, 1), (2, -3)]
    accepted: list[list[str]] = []
    assembled = 0
    well_formed = 0
    rejected = {"malformed_or_partial_stack_program": 0, "public_behavior_disagreed": 0,
                "independent_signature_disagreed": 0}
    for length in range(1, bound + 1):
        for program_tuple in itertools.product(alphabet, repeat=length):
            assembled += 1
            program = list(program_tuple)
            signature = _symbolic_program(program, signatures)
            if signature is None:
                rejected["malformed_or_partial_stack_program"] += 1
                continue
            well_formed += 1
            if any(
                signature[0] * left + signature[1] * right
                != target[0] * left + target[1] * right
                for left, right in cases
            ):
                rejected["public_behavior_disagreed"] += 1
                continue
            if signature != target:
                rejected["independent_signature_disagreed"] += 1
                continue
            accepted.append(program)

    accepted.sort(key=lambda body: (len(body), digest(body)))
    adopted = None
    next_state = None
    if accepted:
        body = accepted[0]
        adopted = _definition(body, _dependency_ids(body), "m100-cycle")
        if register:
            next_state = _state(
                str(checked["inherited_digest"]),
                str(checked["origin_m097_state_digest"]),
                list(checked["operations"]) + [adopted],
            )
            decode_state(canonical_json(next_state).encode("ascii"))
    return {
        "schema": "m100-acquisition-v1",
        "target_signature": list(target),
        "bound": bound,
        "alphabet": alphabet,
        "candidates_assembled": assembled,
        "candidates_well_formed": well_formed,
        "accepted_candidates": len(accepted),
        "shortest_accepted_length": len(accepted[0]) if accepted else None,
        "rejection_counts": rejected,
        "adopted": adopted,
        "registered": bool(adopted and register),
        "next_state": next_state,
    }


def _expression_program(
    body: list[str], definitions: dict[str, dict[str, object]], left: object, right: object
) -> object | None:
    stack: list[object] = []
    for token in body:
        if token == "PUSH_LEFT":
            stack.append(left)
        elif token == "PUSH_RIGHT":
            stack.append(right)
        elif token == "NEG":
            if not stack:
                return None
            stack.append(("neg", stack.pop()))
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        else:
            if len(stack) < 2:
                return None
            call_right = stack.pop()
            call_left = stack.pop()
            if token in {"ADD", "SUB", "MUL"}:
                stack.append((token.lower(), call_left, call_right))
            elif token.startswith("CALL:") and token[5:] in definitions:
                target = definitions[token[5:]]
                expanded = _expression_program(
                    list(target["body"]), definitions, call_left, call_right
                )
                if expanded is None:
                    return None
                stack.append(expanded)
            else:
                return None
    return stack[0] if len(stack) == 1 else None


def live_expression(state: dict[str, object], operation_id: str) -> object:
    checked = decode_state(canonical_json(state).encode("ascii"))
    definitions = {str(item["operation_id"]): item for item in checked["operations"]}
    if operation_id not in definitions:
        raise ValueError("requested operation is not registered")
    expression = _expression_program(
        list(definitions[operation_id]["body"]), definitions, ("left",), ("right",)
    )
    if expression is None:
        raise ValueError("requested operation cannot be expanded")
    return expression


def _affine_source(node: ast.expr) -> tuple[dict[str, int], list[str], str] | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return {node.attr: 1}, [node.attr], node.value.id
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        item = _affine_source(node.operand)
        if item is None:
            return None
        coefficients, order, receiver = item
        return {key: -value for key, value in coefficients.items()}, order, receiver
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        left = _affine_source(node.left)
        right = _affine_source(node.right)
        if left is None or right is None or left[2] != right[2]:
            return None
        sign = 1 if isinstance(node.op, ast.Add) else -1
        coefficients = dict(left[0])
        for key, value in right[0].items():
            coefficients[key] = coefficients.get(key, 0) + sign * value
        order = left[1] + [item for item in right[1] if item not in left[1]]
        return coefficients, order, left[2]
    return None


def observe_requirement(world_root: Path, component: str) -> dict[str, object]:
    component_path = world_root / component
    component_tree = ast.parse(component_path.read_text(encoding="utf-8"))
    declared = {
        node.name: {
            item.target.id for item in node.body
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
        }
        for node in component_tree.body if isinstance(node, ast.ClassDef)
    }
    found: list[tuple[str, str, str, str, int, int]] = []
    for path in sorted(world_root.rglob("*.py")):
        if path.resolve() == component_path.resolve():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for mapping in (node for node in ast.walk(tree) if isinstance(node, ast.Dict)):
            for key, expression in zip(mapping.keys, mapping.values):
                if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                    continue
                affine = _affine_source(expression)
                if affine is None:
                    continue
                coefficients, order, _receiver = affine
                nonzero = [field for field in order if coefficients.get(field, 0)]
                if len(nonzero) != 2:
                    continue
                candidates = [name for name, fields in declared.items() if set(nonzero) <= fields]
                if len(candidates) == 1:
                    left, right = nonzero
                    found.append((
                        candidates[0], key.value, left, right,
                        coefficients[left], coefficients[right],
                    ))
    unique = set(found)
    if len(unique) != 1:
        raise ValueError("fresh runtime observed no unique affine mapping demand")
    class_name, key, left, right, left_coefficient, right_coefficient = unique.pop()
    return {
        "class": class_name,
        "key": key,
        "left_field": left,
        "right_field": right,
        "signature": [left_coefficient, right_coefficient],
        "demand": len(found),
    }


def _expression_ast(expression: object, left_field: str, right_field: str) -> ast.expr:
    kind = expression[0]
    if kind == "left":
        return ast.Attribute(ast.Name("self", ast.Load()), left_field, ast.Load())
    if kind == "right":
        return ast.Attribute(ast.Name("self", ast.Load()), right_field, ast.Load())
    if kind == "neg":
        return ast.UnaryOp(ast.USub(), _expression_ast(expression[1], left_field, right_field))
    operators = {"add": ast.Add(), "sub": ast.Sub(), "mul": ast.Mult()}
    return ast.BinOp(
        _expression_ast(expression[1], left_field, right_field),
        operators[kind],
        _expression_ast(expression[2], left_field, right_field),
    )


def method_ast(requirement: dict[str, object], expression: object) -> ast.FunctionDef:
    return ast.FunctionDef(
        name="as_mapping",
        args=ast.arguments(
            posonlyargs=[], args=[ast.arg(arg="self")], vararg=None,
            kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[],
        ),
        body=[ast.Return(ast.Dict(
            keys=[ast.Constant(requirement["key"])],
            values=[_expression_ast(
                expression, str(requirement["left_field"]), str(requirement["right_field"])
            )],
        ))],
        decorator_list=[], returns=None,
    )


def execute_operation(
    state: dict[str, object],
    operation_id: str,
    world_root: Path,
    component: str,
    cases_path: Path,
) -> dict[str, object]:
    requirement = observe_requirement(world_root, component)
    expression = live_expression(state, operation_id)
    function = method_ast(requirement, expression)
    source = (world_root / component).read_text(encoding="utf-8")
    tree = ast.parse(source)
    target = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef)
         and node.name == requirement["class"]), None
    )
    if target is None:
        raise ValueError("required class is missing from component")
    target.body.append(function)
    module = types.ModuleType("m100_isolated_world")
    module.__file__ = "<m100-isolated-world>"
    sys.modules[module.__name__] = module
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    confirmed = False
    checked_cases = 0
    try:
        exec(compile(ast.fix_missing_locations(tree), module.__file__, "exec"), module.__dict__)
        cls = getattr(module, str(requirement["class"]))
        for case in cases:
            if not isinstance(case, dict):
                raise ValueError("execution case is not an object")
            arguments = case.get("arguments")
            expected = case.get("expected")
            if not isinstance(arguments, dict):
                raise ValueError("execution arguments are invalid")
            if cls(**arguments).as_mapping() != {str(requirement["key"]): expected}:
                break
            checked_cases += 1
        confirmed = bool(cases) and checked_cases == len(cases)
    except Exception:
        confirmed = False
    finally:
        sys.modules.pop(module.__name__, None)
    method_source = ast.unparse(ast.fix_missing_locations(function))
    return {
        "operation_id": operation_id,
        "requirement": requirement,
        "cases": len(cases),
        "cases_passed": checked_cases,
        "confirmed": confirmed,
        "method_source_sha256": hashlib.sha256(method_source.encode("utf-8")).hexdigest(),
    }


def _runtime_envelope(action: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "schema": RUNTIME_SCHEMA,
        "action": action,
        "pid": os.getpid(),
        "isolated_mode": sys.flags.isolated == 1,
        "imported_project_modules": sorted(
            name for name in sys.modules
            if name.startswith(("metamorphosis", "scripts", "mira_core"))
        ),
        "search_path": [str(item) for item in sys.path],
        **payload,
    }


def _write_state(path: str | None, state: dict[str, object]) -> None:
    if path is None:
        raise ValueError("registered state requires an output path")
    Path(path).write_bytes(encode_state(state))


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)

    migrate_parser = subparsers.add_parser("migrate")
    migrate_parser.add_argument("--m097-state", required=True)
    migrate_parser.add_argument("--output-state", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--state", required=True)

    acquire_parser = subparsers.add_parser("acquire")
    acquire_parser.add_argument("--state", required=True)
    acquire_parser.add_argument("--target-left", required=True, type=int)
    acquire_parser.add_argument("--target-right", required=True, type=int)
    acquire_parser.add_argument("--bound", required=True, type=int)
    acquire_parser.add_argument("--register", action="store_true")
    acquire_parser.add_argument("--output-state")

    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--state", required=True)
    execute_parser.add_argument("--operation-id", required=True)
    execute_parser.add_argument("--world-root", required=True)
    execute_parser.add_argument("--component", required=True)
    execute_parser.add_argument("--cases", required=True)

    args = parser.parse_args()
    try:
        if args.action == "migrate":
            state = migrate_m097_state(Path(args.m097_state).read_bytes())
            _write_state(args.output_state, state)
            payload = {
                "confirmed": True,
                "state_digest": state["state_digest"],
                "state_raw_sha256": hashlib.sha256(encode_state(state)).hexdigest(),
                "operations": len(state["operations"]),
            }
        elif args.action == "validate":
            raw = Path(args.state).read_bytes()
            state = decode_state(raw)
            payload = {
                "confirmed": True,
                "state_digest": state["state_digest"],
                "state_raw_sha256": hashlib.sha256(raw).hexdigest(),
                "operations": len(state["operations"]),
                "signatures": {key: list(value) for key, value in operation_signatures(state).items()},
            }
        elif args.action == "acquire":
            state = decode_state(Path(args.state).read_bytes())
            acquisition = acquire(
                state, (args.target_left, args.target_right), args.bound,
                register=args.register,
            )
            if args.register and acquisition["next_state"] is not None:
                _write_state(args.output_state, acquisition["next_state"])
            payload = {
                "confirmed": acquisition["adopted"] is not None,
                "input_state_digest": state["state_digest"],
                "acquisition": {key: value for key, value in acquisition.items() if key != "next_state"},
                "output_state_digest": (
                    acquisition["next_state"]["state_digest"]
                    if acquisition["next_state"] is not None else None
                ),
            }
        else:
            state = decode_state(Path(args.state).read_bytes())
            execution = execute_operation(
                state, args.operation_id, Path(args.world_root), args.component, Path(args.cases)
            )
            payload = {
                "confirmed": execution["confirmed"],
                "state_digest": state["state_digest"],
                "execution": execution,
            }
        result = _runtime_envelope(args.action, payload)
    except Exception as error:  # fail closed with a machine-readable record
        result = _runtime_envelope(args.action or "unknown", {
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
        })
        print(json.dumps(result, sort_keys=True))
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0 if result["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
