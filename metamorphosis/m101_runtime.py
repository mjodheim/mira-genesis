"""M101 carrier-neutral cumulative transfer runtime.

This module contains the bounded mechanism intended for the M101 experiment. It is
stdlib-only and can run from a copied isolated capsule. It deliberately keeps the
M100 predecessor as exact bytes, stores acquired definitions as content-addressed
lineage state, and interprets those definitions over authored carrier-specific atomic
catalogs supplied by each world.

The runtime does not contain a finished composition primitive. A is assembled from a
small carrier-neutral stack language after the producer demand exposes the need for two
ordered atomic effects. B is assembled later from a language in which one live call to
registered A plus one direct atomic effect is the only way to express three effects.

This remains a bounded authored interpreter. It is not self-hosting, unrestricted code
generation, or evidence of open-ended recursive self-improvement.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Callable

STATE_SCHEMA = "m101-lineage-state-v1"
DEFINITION_SCHEMA = "m101-definition-v1"
RUNTIME_SCHEMA = "m101-isolated-runtime-v1"
PUBLIC_DEMAND_SCHEMA = "m101-public-demand-v1"
A_ORIGIN = "m101-a"
B_ORIGIN = "m101-b"

A_TOKENS = (
    "LOAD_INPUT",
    "APPLY_SLOT:0",
    "APPLY_SLOT:1",
    "DUP",
    "SWAP",
    "RETURN",
)
A_MAX_BODY = 5
B_MAX_BODY = 4

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


def public_demand(world: dict[str, Any]) -> dict[str, Any]:
    """Project a world into the only record acquisition and baseline APIs accept.

    The projection is intentionally closed and has no field capable of carrying hidden
    cases. Scientific runners can materialise this record before entering an acquisition
    capsule and bind the exact public case ids that crossed the boundary.
    """
    if not isinstance(world, dict):
        raise ValueError("world is invalid")
    required = {"id", "role", "carrier", "catalog", "public_cases"}
    if not required.issubset(world):
        raise ValueError("world cannot be projected to public demand")
    demand = {
        "schema": PUBLIC_DEMAND_SCHEMA,
        "world_id": world["id"],
        "role": world["role"],
        "carrier": world["carrier"],
        "catalog": copy.deepcopy(world["catalog"]),
        "public_cases": _cases(world["public_cases"], "public demand"),
    }
    return decode_public_demand(demand)


def decode_public_demand(raw: dict[str, Any]) -> dict[str, Any]:
    value = _closed(
        copy.deepcopy(raw),
        {"schema", "world_id", "role", "carrier", "catalog", "public_cases"},
        "M101 public demand",
    )
    if value["schema"] != PUBLIC_DEMAND_SCHEMA:
        raise ValueError("M101 public demand schema mismatch")
    if not isinstance(value["world_id"], str) or not value["world_id"]:
        raise ValueError("M101 public demand world id is invalid")
    if not isinstance(value["role"], str) or not value["role"]:
        raise ValueError("M101 public demand role is invalid")
    if value["carrier"] not in {"text", "record", "syntax"}:
        raise ValueError("M101 public demand carrier is invalid")
    if not isinstance(value["catalog"], list) or not value["catalog"]:
        raise ValueError("M101 public demand catalog is invalid")
    value["public_cases"] = _cases(value["public_cases"], "public demand")
    return value


def _definition_id(origin: str, body: list[str], dependencies: list[str]) -> str:
    payload = {
        "schema": DEFINITION_SCHEMA,
        "origin": origin,
        "body": body,
        "dependencies": dependencies,
    }
    prefix = "generic-combinator" if origin == A_ORIGIN else "syntax-successor"
    return f"{prefix}-{digest(payload)[:16]}"


def definition(origin: str, body: list[str], dependencies: list[str]) -> dict[str, Any]:
    return {
        "schema": DEFINITION_SCHEMA,
        "definition_id": _definition_id(origin, body, dependencies),
        "origin": origin,
        "body": list(body),
        "dependencies": list(dependencies),
    }


def _state(m100_bytes: bytes, definitions: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": STATE_SCHEMA,
        "m100_sha256": sha256_bytes(m100_bytes),
        "m100_ascii": m100_bytes.decode("ascii"),
        "definitions": definitions,
    }
    payload["state_digest"] = digest(payload)
    return payload


def create_state(m100_bytes: bytes) -> dict[str, Any]:
    # The predecessor is intentionally opaque to M101 state construction. Qualification
    # independently verifies that these bytes are the exact frozen M100 S3 state.
    m100_bytes.decode("ascii")
    return _state(m100_bytes, [])


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


def _parse_b_token(token: str) -> tuple[str, tuple[int, ...] | str | None]:
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
        dep = parts[1]
        try:
            return "call", (dep, int(parts[2]), int(parts[3]))
        except ValueError:
            return "invalid", None
    return "invalid", None


def _b_call_order(body: list[str], allowed_dependency: str) -> tuple[int, ...] | None:
    """Return B's semantic slot order under the frozen successor grammar.

    The live A call must occur before the one direct atomic application. This makes the
    transferred capability the mechanism for the first two effects rather than allowing
    the search to hide A in an order-insensitive suffix.
    """
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
                or not isinstance(payload, tuple)
                or len(payload) != 3
            ):
                return None
            dep, left, right = payload
            if dep != allowed_dependency:
                return None
            call_count += 1
            call_seen = True
            order.extend([int(left), int(right)])
        elif kind == "apply":
            if not loaded or not call_seen or not isinstance(payload, tuple):
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


def decode_state(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        value = copy.deepcopy(raw)
    else:
        if isinstance(raw, str):
            raw_bytes = raw.encode("ascii")
        else:
            raw_bytes = raw
        try:
            decoded = raw_bytes.decode("ascii")
            value = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"M101 state is not canonical ASCII JSON: {error}") from error
        if canonical_json(value).encode("ascii") != raw_bytes:
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
        if not isinstance(item["body"], list) or not all(isinstance(t, str) for t in item["body"]):
            raise ValueError("M101 definition body is invalid")
        if not isinstance(item["dependencies"], list) or not all(
            isinstance(dep, str) for dep in item["dependencies"]
        ):
            raise ValueError("M101 dependency list is invalid")
        if item["definition_id"] != _definition_id(
            str(item["origin"]), list(item["body"]), list(item["dependencies"])
        ):
            raise ValueError("M101 content-addressed definition id mismatch")
        if any(dep not in seen for dep in item["dependencies"]):
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
                raise ValueError("A contains a forbidden carrier/shortcut identifier")
            a_id = str(item["definition_id"])
        else:
            if item["origin"] != B_ORIGIN or a_id is None:
                raise ValueError("only B may follow A")
            if item["dependencies"] != [a_id]:
                raise ValueError("B does not retain exactly one live A dependency")
            b_order = _b_call_order(list(item["body"]), a_id)
            if b_order is None or sorted(b_order) != [0, 1, 2]:
                raise ValueError("B does not encode the required three-effect order through A")
        seen[str(item["definition_id"])] = item
    return value


def encode_state(state: dict[str, Any]) -> bytes:
    checked = decode_state(state)
    return canonical_json(checked).encode("ascii")


def register(state: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    definitions = copy.deepcopy(checked["definitions"])
    definitions.append(copy.deepcopy(item))
    next_state = _state(checked["m100_ascii"].encode("ascii"), definitions)
    return decode_state(next_state)


def definition_by_id(state: dict[str, Any], definition_id: str) -> dict[str, Any]:
    checked = decode_state(state)
    for item in checked["definitions"]:
        if item["definition_id"] == definition_id:
            return item
    raise KeyError(definition_id)


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
                    for arg in node.args.args:
                        if arg.arg == old:
                            arg.arg = new
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
        doc = descriptor["text"]

        class Transform(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
                self.generic_visit(node)
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    node.body.insert(0, ast.Expr(value=ast.Constant(value=doc)))
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


def build_catalog(world: dict[str, Any]) -> list[Atomic]:
    carrier = world.get("carrier")
    catalog = world.get("catalog")
    if carrier not in {"text", "record", "syntax"} or not isinstance(catalog, list):
        raise ValueError("world carrier/catalog is invalid")
    atomics = [atomic_from_descriptor(str(carrier), item) for item in catalog]
    if len({atomic.identity for atomic in atomics}) != len(atomics):
        raise ValueError("world contains duplicate atomic descriptors")
    return atomics


def _single_atomic_reachable(
    public_cases: list[dict[str, Any]], catalog: list[Atomic]
) -> bool:
    """Return whether one inherited atomic alone satisfies the public demand.

    This is deliberately not implemented through a variable-length pipeline helper.
    T0's executable candidate image is the finite set of single atomic applications.
    """
    for atomic in catalog:
        try:
            if all(
                atomic.apply(copy.deepcopy(case["input"])) == case["expected"]
                for case in public_cases
            ):
                return True
        except Exception:
            continue
    return False


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
    """Resolve opaque slots only by executing the candidate/registered A body.

    The removed v3 implementation first executed a host-side list pipeline and could
    therefore solve a two-effect demand at T0 without A.  Here every two-effect trial
    is mediated by the explicit body under test.  With no body in lineage state, this
    operation is unavailable to the consumer baseline.
    """
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


def acquire_a(
    state: dict[str, Any], demand: dict[str, Any], *, register_result: bool
) -> dict[str, Any]:
    checked = decode_state(state)
    if checked["definitions"]:
        raise ValueError("A acquisition requires T0")
    public = decode_public_demand(demand)
    if public["carrier"] != "text" or public["role"] != "producer_trigger":
        raise ValueError("A acquisition may consume only the text producer trigger")
    public_cases = public["public_cases"]
    public_case_ids = [case["case_id"] for case in public_cases]
    catalog = build_catalog(public)
    one_reachable = _single_atomic_reachable(public_cases, catalog)
    if one_reachable:
        return {
            "schema": "m101-a-acquisition-v1",
            "confirmed": False,
            "single_atomic_reachable": one_reachable,
            "assembled": 0,
            "well_formed": 0,
            "accepted": 0,
            "adopted": None,
            "registered": False,
            "next_state": None,
            "public_case_ids": public_case_ids,
        }
    assembled = 0
    well_formed = 0
    binding_candidates_evaluated = 0
    accepted: list[tuple[list[str], list[int], dict[str, Any]]] = []
    for length in range(1, A_MAX_BODY + 1):
        for body_tuple in itertools.product(A_TOKENS, repeat=length):
            assembled += 1
            body = list(body_tuple)
            if _a_call_order(body) is None:
                continue
            well_formed += 1
            binding, binding_report = _a_bindings(body, public_cases, catalog)
            binding_candidates_evaluated += int(binding_report["assembled"])
            if binding is not None:
                accepted.append((body, binding, binding_report))
    accepted.sort(key=lambda item: (len(item[0]), digest(item[0])))
    if not accepted:
        return {
            "schema": "m101-a-acquisition-v1",
            "confirmed": False,
            "single_atomic_reachable": False,
            "assembled": assembled,
            "well_formed": well_formed,
            "binding_candidates_evaluated": binding_candidates_evaluated,
            "accepted": 0,
            "adopted": None,
            "registered": False,
            "next_state": None,
            "public_case_ids": public_case_ids,
        }
    selected_body, selected_binding, selected_binding_report = accepted[0]
    adopted = definition(A_ORIGIN, selected_body, [])
    next_state = register(checked, adopted) if register_result else None
    return {
        "schema": "m101-a-acquisition-v1",
        "confirmed": True,
        "single_atomic_reachable": False,
        "inferred_slot_indices": selected_binding,
        "binding_search": selected_binding_report,
        "assembled": assembled,
        "well_formed": well_formed,
        "binding_candidates_evaluated": binding_candidates_evaluated,
        "accepted": len(accepted),
        "shortest_accepted_length": len(selected_body),
        "adopted": adopted,
        "registered": bool(register_result),
        "next_state": next_state,
        "public_case_ids": public_case_ids,
    }


def _execute_b_body(
    body: list[str], state: dict[str, Any], value: Any, slots: tuple[Atomic, Atomic, Atomic]
) -> Any | None:
    checked = decode_state(state)
    a = checked["definitions"][0] if checked["definitions"] else None
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
            if not loaded or a is None or not isinstance(payload, tuple) or len(payload) != 3:
                return None
            dep, left, right = payload
            if dep != a["definition_id"]:
                return None
            current = _execute_a_body(
                list(a["body"]), current, (slots[int(left)], slots[int(right)])
            )
            if current is None:
                return None
        elif kind == "apply":
            if not loaded or not isinstance(payload, tuple):
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
    """Resolve three opaque slots only through the candidate B body and live A."""
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


def acquire_b(
    state: dict[str, Any], demand: dict[str, Any], *, register_result: bool
) -> dict[str, Any]:
    checked = decode_state(state)
    public = decode_public_demand(demand)
    public_case_ids = [case["case_id"] for case in public["public_cases"]]
    if len(checked["definitions"]) != 1:
        return {
            "schema": "m101-b-acquisition-v1",
            "confirmed": False,
            "reason": "registered A is required",
            "assembled": 0,
            "well_formed": 0,
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "public_case_ids": public_case_ids,
        }
    if public["carrier"] != "syntax" or public["role"] != "b_reuse":
        raise ValueError("B acquisition requires a syntax B world")
    a = checked["definitions"][0]
    a_id = str(a["definition_id"])
    public_cases = public["public_cases"]
    catalog = build_catalog(public)

    alphabet = [
        "LOAD_INPUT",
        "RETURN",
        "APPLY_SLOT:0",
        "APPLY_SLOT:1",
        "APPLY_SLOT:2",
    ] + [f"CALL:{a_id}:{left}:{right}" for left in range(3) for right in range(3)]
    assembled = 0
    well_formed = 0
    binding_candidates_evaluated = 0
    accepted: list[tuple[list[str], list[int], dict[str, Any]]] = []
    for length in range(1, B_MAX_BODY + 1):
        for body_tuple in itertools.product(alphabet, repeat=length):
            assembled += 1
            body = list(body_tuple)
            b_order = _b_call_order(body, a_id)
            if b_order is None or any(slot not in {0, 1, 2} for slot in b_order):
                continue
            well_formed += 1
            binding, binding_report = _b_bindings(body, checked, public_cases, catalog)
            binding_candidates_evaluated += int(binding_report["assembled"])
            if binding is not None:
                accepted.append((body, binding, binding_report))
    accepted.sort(key=lambda item: (len(item[0]), digest(item[0])))
    if not accepted:
        return {
            "schema": "m101-b-acquisition-v1",
            "confirmed": False,
            "assembled": assembled,
            "well_formed": well_formed,
            "binding_candidates_evaluated": binding_candidates_evaluated,
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "public_case_ids": public_case_ids,
        }
    selected_body, selected_binding, selected_binding_report = accepted[0]
    adopted = definition(B_ORIGIN, selected_body, [a_id])
    next_state = register(checked, adopted) if register_result else None
    return {
        "schema": "m101-b-acquisition-v1",
        "confirmed": True,
        "inferred_slot_indices": selected_binding,
        "binding_search": selected_binding_report,
        "assembled": assembled,
        "well_formed": well_formed,
        "binding_candidates_evaluated": binding_candidates_evaluated,
        "accepted": len(accepted),
        "shortest_accepted_length": len(selected_body),
        "adopted": adopted,
        "registered": bool(register_result),
        "next_state": next_state,
        "public_case_ids": public_case_ids,
    }


def rewrite_a_order_for_fault(state: dict[str, Any]) -> dict[str, Any]:
    """Create a digest-valid fault by replacing A's second effect with its first.

    The dependent B is re-addressed so the content-addressed dependency graph remains valid;
    no semantic repair is performed. Normal ``decode_state`` accepts the mutated state because
    state validity is distinct from the canonical experiment's accepted A semantics.
    """
    checked = decode_state(state)
    if len(checked["definitions"]) != 2:
        raise ValueError("T2 is required for the live mutation control")
    old_a, old_b = copy.deepcopy(checked["definitions"])
    mutated_a = definition(A_ORIGIN, ["LOAD_INPUT", "APPLY_SLOT:0", "APPLY_SLOT:0", "RETURN"], [])
    old_id = str(old_a["definition_id"])
    new_id = str(mutated_a["definition_id"])
    new_b_body = [
        token.replace(f"CALL:{old_id}:", f"CALL:{new_id}:") if token.startswith("CALL:") else token
        for token in old_b["body"]
    ]
    mutated_b = definition(B_ORIGIN, new_b_body, [new_id])
    return decode_state(_state(checked["m100_ascii"].encode("ascii"), [mutated_a, mutated_b]))


def ablate_a_raw(state: dict[str, Any]) -> bytes:
    checked = decode_state(state)
    payload = {
        "schema": STATE_SCHEMA,
        "m100_sha256": checked["m100_sha256"],
        "m100_ascii": checked["m100_ascii"],
        "definitions": checked["definitions"][1:],
    }
    payload["state_digest"] = digest(payload)
    return canonical_json(payload).encode("ascii")


def ablate_b(state: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    if not checked["definitions"]:
        return checked
    return _state(checked["m100_ascii"].encode("ascii"), checked["definitions"][:1])


def corrupt_state_digest(state: dict[str, Any]) -> bytes:
    checked = decode_state(state)
    corrupted = copy.deepcopy(checked)
    old = str(corrupted["state_digest"])
    corrupted["state_digest"] = ("0" if old[0] != "0" else "1") + old[1:]
    return canonical_json(corrupted).encode("ascii")


def accepted_state_summary(state: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    return {
        "state_digest": checked["state_digest"],
        "m100_sha256": checked["m100_sha256"],
        "definition_count": len(checked["definitions"]),
        "definition_ids": [item["definition_id"] for item in checked["definitions"]],
        "definition_bodies": [item["body"] for item in checked["definitions"]],
    }
