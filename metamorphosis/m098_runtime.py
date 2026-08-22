"""Minimal generic M098 runtime capsule.

This file deliberately imports no Mira module.  The M098 runner copies it into an
isolated directory containing no acquisition, validator, qualification or repository
package.  A fresh ``python -I`` process decodes persisted operation-language state,
observes one binary mapping demand from real Python source, interprets registered stack
definitions into AST, and execution-checks the resulting method.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import types
from pathlib import Path

LANGUAGE_SCHEMA = "m097-operation-language-v1"
DEFINITION_SCHEMA = "m097-expression-operation-v1"
RUNTIME_SCHEMA = "m098-fresh-runtime-v1"
TOKENS = {"PUSH_LEFT", "PUSH_RIGHT", "ADD", "SUB", "MUL", "NEG", "SWAP"}
MAX_BODY = 4


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def decode_state(raw: bytes) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"state is not canonical ASCII JSON: {error}") from error
    if not isinstance(value, dict) or set(value) != {
        "schema", "inherited_digest", "extensions", "state_digest"
    }:
        raise ValueError("state is not a closed operation-language record")
    recorded = value["state_digest"]
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    if recorded != digest(payload):
        raise ValueError("state digest mismatch")
    if value["schema"] != LANGUAGE_SCHEMA or not isinstance(value["inherited_digest"], str):
        raise ValueError("state schema or inherited digest is invalid")
    extensions = value["extensions"]
    if not isinstance(extensions, list):
        raise ValueError("extensions are not a list")
    for definition in extensions:
        if not isinstance(definition, dict) or set(definition) != {"schema", "body"}:
            raise ValueError("extension is not a closed definition")
        body = definition["body"]
        if definition["schema"] != DEFINITION_SCHEMA:
            raise ValueError("extension schema is invalid")
        if not isinstance(body, list) or not 0 < len(body) <= MAX_BODY:
            raise ValueError("extension body is empty or over bound")
        if not all(isinstance(token, str) and token in TOKENS for token in body):
            raise ValueError("extension body uses an unknown token")
    return value


def _operator(node: ast.operator) -> str | None:
    if isinstance(node, ast.Sub):
        return "sub"
    if isinstance(node, ast.Add):
        return "add"
    if isinstance(node, ast.Mult):
        return "mul"
    return None


def observe_requirement(world_root: Path, component: str) -> dict[str, object]:
    component_path = world_root / component
    component_tree = ast.parse(component_path.read_text(encoding="utf-8"))
    classes = [node for node in component_tree.body if isinstance(node, ast.ClassDef)]
    fields = {
        node.name: {
            item.target.id for item in node.body
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
        }
        for node in classes
    }
    found = []
    for path in sorted(world_root.rglob("*.py")):
        if path.resolve() == component_path.resolve():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for mapping in (node for node in ast.walk(tree) if isinstance(node, ast.Dict)):
            for key, value in zip(mapping.keys, mapping.values):
                if not (
                    isinstance(key, ast.Constant) and isinstance(key.value, str)
                    and isinstance(value, ast.BinOp)
                    and isinstance(value.left, ast.Attribute)
                    and isinstance(value.right, ast.Attribute)
                    and isinstance(value.left.value, ast.Name)
                    and isinstance(value.right.value, ast.Name)
                    and value.left.value.id == value.right.value.id
                ):
                    continue
                operator = _operator(value.op)
                candidates = [
                    name for name, declared in fields.items()
                    if {value.left.attr, value.right.attr} <= declared
                ]
                if operator and len(candidates) == 1:
                    found.append((
                        candidates[0], key.value, value.left.attr, operator, value.right.attr
                    ))
    unique = set(found)
    if len(unique) != 1:
        raise ValueError("fresh runtime observed no unique binary mapping demand")
    class_name, key, left, operator, right = unique.pop()
    return {
        "class": class_name, "key": key, "left_field": left,
        "operator": operator, "right_field": right, "demand": len(found)
    }


def symbolic(body: list[str]):
    stack = []
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
        else:
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            stack.append((token.lower(), left, right))
    return stack[0] if len(stack) == 1 else None


def expression_ast(symbol, left_field: str, right_field: str) -> ast.expr:
    if symbol[0] == "left":
        return ast.Attribute(ast.Name("self", ast.Load()), left_field, ast.Load())
    if symbol[0] == "right":
        return ast.Attribute(ast.Name("self", ast.Load()), right_field, ast.Load())
    if symbol[0] == "neg":
        return ast.UnaryOp(ast.USub(), expression_ast(symbol[1], left_field, right_field))
    operators = {"add": ast.Add(), "sub": ast.Sub(), "mul": ast.Mult()}
    return ast.BinOp(
        expression_ast(symbol[1], left_field, right_field),
        operators[symbol[0]],
        expression_ast(symbol[2], left_field, right_field),
    )


def method_ast(requirement: dict[str, object], body: list[str]) -> ast.FunctionDef | None:
    symbol = symbolic(body)
    if symbol is None:
        return None
    return ast.FunctionDef(
        name="as_mapping",
        args=ast.arguments(
            posonlyargs=[], args=[ast.arg(arg="self")], vararg=None,
            kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]
        ),
        body=[ast.Return(ast.Dict(
            keys=[ast.Constant(requirement["key"])],
            values=[expression_ast(
                symbol, str(requirement["left_field"]), str(requirement["right_field"])
            )],
        ))],
        decorator_list=[], returns=None, type_params=[]
    )


def expected_value(requirement: dict[str, object], arguments: dict[str, object]):
    left = arguments[str(requirement["left_field"])]
    right = arguments[str(requirement["right_field"])]
    operator = requirement["operator"]
    if operator == "sub":
        return left - right
    if operator == "add":
        return left + right
    if operator == "mul":
        return left * right
    raise ValueError("unsupported observed operator")


def execute_candidate(
    source: str,
    requirement: dict[str, object],
    function: ast.FunctionDef,
    cases: list[dict[str, object]],
) -> bool:
    tree = ast.parse(source)
    target = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef)
         and node.name == requirement["class"]), None
    )
    if target is None:
        return False
    target.body.append(function)
    tree = ast.fix_missing_locations(tree)
    module_name = "m098_isolated_world"
    module = types.ModuleType(module_name)
    module.__file__ = "<m098-isolated-world>"
    sys.modules[module_name] = module
    try:
        exec(compile(tree, module.__file__, "exec"), module.__dict__)
        cls = getattr(module, str(requirement["class"]))
        for case in cases:
            arguments = case.get("arguments")
            if not isinstance(arguments, dict):
                return False
            instance = cls(**arguments)
            produced = instance.as_mapping()
            expected = {str(requirement["key"]): expected_value(requirement, arguments)}
            if produced != expected:
                return False
        return bool(cases)
    except Exception:
        return False
    finally:
        sys.modules.pop(module_name, None)


def run(state_path: Path, world_root: Path, component: str, cases_path: Path) -> dict[str, object]:
    raw = state_path.read_bytes()
    state = decode_state(raw)
    requirement = observe_requirement(world_root, component)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    source = (world_root / component).read_text(encoding="utf-8")
    confirmed = False
    method_source = None
    tested = 0
    for definition in state["extensions"]:
        function = method_ast(requirement, definition["body"])
        if function is None:
            continue
        tested += 1
        if execute_candidate(source, requirement, function, cases):
            confirmed = True
            method_source = ast.unparse(ast.fix_missing_locations(function))
            break
    imported_project_modules = sorted(
        name for name in sys.modules
        if name.startswith(("metamorphosis", "scripts", "mira_core"))
    )
    search_path = [str(item) for item in sys.path]
    return {
        "schema": RUNTIME_SCHEMA,
        "pid": os.getpid(),
        "isolated_mode": sys.flags.isolated == 1,
        "state_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "state_digest": state["state_digest"],
        "extensions_loaded": len(state["extensions"]),
        "extensions_tested": tested,
        "requirement": requirement,
        "cases": len(cases),
        "confirmed": confirmed,
        "method_source_sha256": (
            hashlib.sha256(method_source.encode("utf-8")).hexdigest()
            if method_source else None
        ),
        "imported_project_modules": imported_project_modules,
        "search_path": search_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--world-root", required=True)
    parser.add_argument("--component", required=True)
    parser.add_argument("--cases", required=True)
    args = parser.parse_args()
    try:
        result = run(
            Path(args.state), Path(args.world_root), args.component, Path(args.cases)
        )
    except Exception as error:  # fail closed and preserve a machine-readable record
        print(json.dumps({
            "schema": RUNTIME_SCHEMA,
            "pid": os.getpid(),
            "isolated_mode": sys.flags.isolated == 1,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
            "imported_project_modules": sorted(
                name for name in sys.modules
                if name.startswith(("metamorphosis", "scripts", "mira_core"))
            ),
            "search_path": [str(item) for item in sys.path],
        }, sort_keys=True))
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0 if result["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
