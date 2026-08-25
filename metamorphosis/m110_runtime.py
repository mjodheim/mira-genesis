"""M110 - a consumer family that took no part in producing the machinery it is handed.

M109 qualified two successive lineage-acquired machinery generations inside one three-signal Boolean
laboratory. This module is a **different laboratory**, and it holds no producer-domain content at
all: no Boolean world, no M109 target, no rule body, no truth table, no digest.

What it does hold is an adapter. The consumer registers the same three components under the same
names and computes the same three failure features under their declared semantics, and then asks
``m109_runtime.attribute`` -- imported unchanged, never reimplemented -- which component to extend.
The rule cascade that answers is restored from the frozen M109 result elsewhere; nothing here knows
what it says.

The carrier is a list of JSON documents over the chain ``0 < 1 < 2 < 3``, plus a **side table**. A
document's latent field lives in a different document, reached by following the document's reference.
No interface width exposes it; only adopting an *accessor* does. That single structural fact decouples
"the interface cannot read it" from "no operator can reach it" -- which is exactly the implication the
producer's prefix-truncated Boolean world enforces and this one does not.

Expressions are evaluated two independent ways: by a small interpreter that holds no operator
semantics (the operators are data, as in M107), and by rendering the expression as Python source,
compiling it and executing it against the parsed documents. Agreement between the two is measured.
"""

from __future__ import annotations

import itertools
import json
from typing import Any, Iterable

from metamorphosis import m109_runtime as lineage

STATE_SCHEMA = "m110-consumer-state-v1"
WORLD_SCHEMA = "m110-consumer-world-v1"
OPERATOR_SCHEMA = "m110-consumer-operator-v1"
DEMAND_SCHEMA = "m110-consumer-demand-v1"
POPULATION_SCHEMA = "m110-consumer-population-v1"

# The registry and the feature vocabulary are shared authored vocabulary, not transferred content.
# They are read from the producer module rather than restated, so a drift is an import error here
# instead of a silent disagreement about what a rule selects.
COMPONENT_OPERATORS = lineage.COMPONENT_OPERATORS
COMPONENT_SIGNALS = lineage.COMPONENT_SIGNALS
COMPONENT_CANDIDATES = lineage.COMPONENT_CANDIDATES
COMPONENTS = lineage.COMPONENTS
FEATURE_NAMES = lineage.FEATURE_NAMES
FEATURE_COUNT = lineage.FEATURE_COUNT
FEATURE_ROWS = lineage.FEATURE_ROWS

MONOTONE_SPACE = lineage.MONOTONE_SPACE
COMPLETE_SPACE = lineage.COMPLETE_SPACE
CANDIDATE_SPACES = lineage.CANDIDATE_SPACES

# The consumer's own dimensions. None of these appear in the producer.
VALUES: tuple[int, ...] = (0, 1, 2, 3)
VISIBLE_FIELDS: tuple[str, ...] = ("alpha", "beta", "gamma")
REFERENCE_FIELD = "ref"
DOCUMENT_COUNT = 5
BASE_INTERFACE_WIDTH = 2
MAX_INTERFACE_WIDTH = len(VISIBLE_FIELDS)
MAX_EXPRESSION_NODES = 9
DEEPER_EXPRESSION_NODES = 13
FIXED_POINT_BOUNDS: tuple[int, ...] = (7, 9, 11, 13)
MACHINERY_STEP_BUDGET = 1

canonical_json = lineage.canonical_json
digest = lineage.digest
sha256_bytes = lineage.sha256_bytes


# ----------------------------------------------------------------------------------------
# Operators are data. The interpreter below knows none of them.
# ----------------------------------------------------------------------------------------


def binary_operator(name: str, table: Iterable[int]) -> dict[str, Any]:
    rows = [int(value) for value in table]
    if len(rows) != len(VALUES) ** 2 or any(value not in VALUES for value in rows):
        raise ValueError("M110 binary operator table is invalid")
    return _identified({"schema": OPERATOR_SCHEMA, "kind": "binary", "name": name, "table": rows})


def map_operator(name: str, table: Iterable[int]) -> dict[str, Any]:
    rows = [int(value) for value in table]
    if len(rows) != len(VALUES) or any(value not in VALUES for value in rows):
        raise ValueError("M110 map operator table is invalid")
    return _identified({"schema": OPERATOR_SCHEMA, "kind": "map", "name": name, "table": rows})


def access_operator(name: str, path: Iterable[str]) -> dict[str, Any]:
    keys = [str(item) for item in path]
    if not keys:
        raise ValueError("M110 accessor path is empty")
    return _identified({"schema": OPERATOR_SCHEMA, "kind": "access", "name": name, "path": keys})


def _identified(payload: dict[str, Any]) -> dict[str, Any]:
    payload["operator_id"] = "consumer-operator-" + digest(payload)[:16]
    return payload


def decode_operator(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != OPERATOR_SCHEMA:
        raise ValueError("M110 operator payload is invalid")
    kind = raw.get("kind")
    if kind == "binary":
        rebuilt = binary_operator(raw.get("name"), raw.get("table") or [])
    elif kind == "map":
        rebuilt = map_operator(raw.get("name"), raw.get("table") or [])
    elif kind == "access":
        rebuilt = access_operator(raw.get("name"), raw.get("path") or [])
    else:
        raise ValueError("M110 operator kind is outside the authored registry")
    if rebuilt["operator_id"] != raw.get("operator_id"):
        raise ValueError("M110 operator identity mismatch")
    return rebuilt


def initial_operators() -> list[dict[str, Any]]:
    """The lattice fragment of the chain. Closed under itself, exactly as ``{AND, OR}`` is."""
    return [
        binary_operator("MIN", [min(a, b) for a in VALUES for b in VALUES]),
        binary_operator("MAX", [max(a, b) for a in VALUES for b in VALUES]),
    ]


def map_space() -> list[dict[str, Any]]:
    """Every unary map of the chain to itself. The host codes the space, never the answer."""
    return [
        map_operator("CMAP_%03d" % index, list(table))
        for index, table in enumerate(itertools.product(VALUES, repeat=len(VALUES)))
    ]


def map_is_monotone(operator: dict[str, Any]) -> bool:
    table = operator["table"]
    return all(table[index] <= table[index + 1] for index in range(len(table) - 1))


# ----------------------------------------------------------------------------------------
# The consumer world: JSON documents, a side table, and one reference edge per document.
# ----------------------------------------------------------------------------------------


def consumer_world(
    world_id: str, documents: Iterable[dict[str, Any]], side: dict[str, Any]
) -> dict[str, Any]:
    docs = [dict(item) for item in documents]
    if len(docs) != DOCUMENT_COUNT:
        raise ValueError("M110 world document count is outside the authored ceiling")
    for document in docs:
        for field in VISIBLE_FIELDS:
            if document.get(field) not in VALUES:
                raise ValueError("M110 document field is outside the value chain")
        if document.get(REFERENCE_FIELD) not in side:
            raise ValueError("M110 document reference does not resolve")
    payload = {
        "schema": WORLD_SCHEMA,
        "world_id": str(world_id),
        "documents": docs,
        "side": {str(key): dict(value) for key, value in sorted(side.items())},
        "visible_fields": list(VISIBLE_FIELDS),
    }
    payload["world_digest"] = digest(payload)
    return payload


def decode_world(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != WORLD_SCHEMA:
        raise ValueError("M110 world payload is invalid")
    rebuilt = consumer_world(raw.get("world_id"), raw.get("documents") or [], raw.get("side") or {})
    if rebuilt["world_digest"] != raw.get("world_digest"):
        raise ValueError("M110 world identity mismatch")
    return rebuilt


def accessor_paths(world: dict[str, Any]) -> list[list[str]]:
    """Every side-document key path whose values all lie in the chain, in canonical order.

    Derived from the world's own structure. Nothing here names a field: a side document holding a
    string note contributes no accessor because its values are not chain values, and it would
    contribute one if they were.
    """
    documents = world["documents"]
    side = world["side"]
    keys: set[str] = set()
    for document in documents:
        keys |= set(side[document[REFERENCE_FIELD]])
    usable = []
    for key in sorted(keys):
        values = [side[document[REFERENCE_FIELD]].get(key) for document in documents]
        if all(value in VALUES for value in values):
            usable.append([key])
    return usable


def accessor_operators(world: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        access_operator("DEREF_" + ".".join(path), path) for path in accessor_paths(world)
    ]


def full_signal_vectors(world: dict[str, Any]) -> tuple[tuple[int, ...], ...]:
    """Visible fields followed by every accessor-reachable value, in canonical order."""
    paths = accessor_paths(world)
    side = world["side"]
    rows = []
    for document in world["documents"]:
        latent = tuple(side[document[REFERENCE_FIELD]][path[0]] for path in paths)
        rows.append(tuple(document[field] for field in VISIBLE_FIELDS) + latent)
    return tuple(rows)


def visible_vectors(world: dict[str, Any], width: int) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(document[field] for field in VISIBLE_FIELDS[:width])
        for document in world["documents"]
    )


def is_function_of_visible(world: dict[str, Any], target: Iterable[int], width: int) -> bool:
    """The general form of the producer's ``depends_on_signal``.

    In a world whose rows are every signal vector the two coincide exactly; in a world with authored
    documents this one is the meaningful reading. It says nothing about which component to extend --
    at row 5 it is true while the operator table is the answer.
    """
    seen: dict[tuple[int, ...], int] = {}
    for key, value in zip(visible_vectors(world, width), target):
        if seen.setdefault(key, value) != value:
            return False
    return True


def is_monotone(world: dict[str, Any], target: Iterable[int]) -> bool:
    values = list(target)
    rows = full_signal_vectors(world)
    for i, left in enumerate(rows):
        for j, right in enumerate(rows):
            if i == j:
                continue
            if all(a <= b for a, b in zip(left, right)) and values[i] > values[j]:
                return False
    return True


# ----------------------------------------------------------------------------------------
# The interpreter. It holds no operator semantics; operators are looked up in the state.
# ----------------------------------------------------------------------------------------


def field_node(field: str) -> dict[str, Any]:
    return {"node": "FIELD", "field": field}


def access_node(operator: str) -> dict[str, Any]:
    return {"node": "ACCESS", "operator": operator}


def map_node(operator: str, child: dict[str, Any]) -> dict[str, Any]:
    return {"node": "MAP", "operator": operator, "child": child}


def join_node(operator: str, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {"node": "JOIN", "operator": operator, "left": left, "right": right}


def node_count(expression: dict[str, Any]) -> int:
    kind = expression.get("node")
    if kind in ("FIELD", "ACCESS"):
        return 1
    if kind == "MAP":
        return 1 + node_count(expression["child"])
    if kind == "JOIN":
        return 1 + node_count(expression["left"]) + node_count(expression["right"])
    raise ValueError("M110 expression node is invalid")


def execute_expression(
    operators: dict[str, dict[str, Any]],
    expression: dict[str, Any],
    world: dict[str, Any],
    document: dict[str, Any],
) -> int:
    side = world["side"]

    def run(node: dict[str, Any]) -> int:
        kind = node.get("node")
        if kind == "FIELD":
            if node["field"] not in VISIBLE_FIELDS:
                raise ValueError("M110 expression reads a field outside the authored record")
            return int(document[node["field"]])
        operator = operators.get(node.get("operator"))
        if operator is None:
            raise ValueError("M110 expression names an operator the state does not hold")
        if kind == "ACCESS":
            value = side[document[REFERENCE_FIELD]]
            for key in operator["path"]:
                value = value[key]
            return int(value)
        if kind == "MAP":
            return int(operator["table"][run(node["child"])])
        if kind == "JOIN":
            return int(operator["table"][run(node["left"]) * len(VALUES) + run(node["right"])])
        raise ValueError("M110 expression node is invalid")

    return run(expression)


def evaluate(
    operators: Iterable[dict[str, Any]], expression: dict[str, Any], world: dict[str, Any]
) -> tuple[int, ...]:
    table = {item["name"]: item for item in operators}
    return tuple(
        execute_expression(table, expression, world, document) for document in world["documents"]
    )


# ----------------------------------------------------------------------------------------
# The second, independent execution path: render the expression as Python and run it.
# ----------------------------------------------------------------------------------------


def render_python(operators: Iterable[dict[str, Any]], expression: dict[str, Any]) -> str:
    """Emit a self-contained module whose ``transform(document, side)`` realizes the expression."""
    table = {item["name"]: item for item in operators}

    def emit(node: dict[str, Any]) -> str:
        kind = node["node"]
        if kind == "FIELD":
            return "document[%s]" % json.dumps(node["field"])
        operator = table[node["operator"]]
        if kind == "ACCESS":
            source = "side[document[%s]]" % json.dumps(REFERENCE_FIELD)
            for key in operator["path"]:
                source += "[%s]" % json.dumps(key)
            return source
        if kind == "MAP":
            return "%s[%s]" % (json.dumps(operator["table"]), emit(node["child"]))
        return "%s[(%s) * %d + (%s)]" % (
            json.dumps(operator["table"]),
            emit(node["left"]),
            len(VALUES),
            emit(node["right"]),
        )

    return "def transform(document, side):\n    return %s\n" % emit(expression)


def execute_rendered(
    operators: Iterable[dict[str, Any]], expression: dict[str, Any], world: dict[str, Any]
) -> tuple[int, ...]:
    source = render_python(operators, expression)
    namespace: dict[str, Any] = {}
    exec(compile(source, "<m110-consumer>", "exec"), {"__builtins__": {}}, namespace)  # noqa: S102
    transform = namespace["transform"]
    return tuple(int(transform(document, world["side"])) for document in world["documents"])


# ----------------------------------------------------------------------------------------
# Lineage state. Everything except ``rules`` is the adapter and is identical across arms.
# ----------------------------------------------------------------------------------------


def create_state(
    operators: Iterable[dict[str, Any]] | None = None,
    *,
    interface_width: int = BASE_INTERFACE_WIDTH,
    candidate_space: str = MONOTONE_SPACE,
    rules: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    width = int(interface_width)
    if width not in range(1, MAX_INTERFACE_WIDTH + 1):
        raise ValueError("M110 interface width is outside the authored ceiling")
    if candidate_space not in CANDIDATE_SPACES:
        raise ValueError("M110 candidate space is outside the authored registry")
    cascade = [lineage.decode_rule(item) for item in (rules or [])]
    source = list(operators) if operators is not None else initial_operators()
    payload = {
        "operators": [decode_operator(item) for item in source],
        "interface_width": width,
        "candidate_space": candidate_space,
        "rules": cascade,
        "component_registry": list(COMPONENTS),
        "feature_vocabulary": list(FEATURE_NAMES),
    }
    return {"schema": STATE_SCHEMA, **payload, "state_digest": digest(payload)}


def decode_state(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        value = json.loads(bytes(raw).decode("ascii"))
    elif isinstance(raw, str):
        value = json.loads(raw)
    else:
        value = json.loads(canonical_json(raw))
    if not isinstance(value, dict) or value.get("schema") != STATE_SCHEMA:
        raise ValueError("M110 consumer state payload is invalid")
    if list(value.get("component_registry") or []) != list(COMPONENTS):
        raise ValueError("M110 component registry changed")
    if list(value.get("feature_vocabulary") or []) != list(FEATURE_NAMES):
        raise ValueError("M110 feature vocabulary changed")
    rebuilt = create_state(
        value.get("operators") or [],
        interface_width=int(value.get("interface_width", BASE_INTERFACE_WIDTH)),
        candidate_space=value.get("candidate_space", MONOTONE_SPACE),
        rules=value.get("rules") or [],
    )
    if rebuilt["state_digest"] != value.get("state_digest"):
        raise ValueError("M110 consumer state digest mismatch")
    return rebuilt


def encode_state(state: dict[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


def adapter_projection(state: dict[str, Any]) -> dict[str, Any]:
    """Everything except the cascade. Equal across arms is a measured predicate, not a promise."""
    return {key: value for key, value in decode_state(state).items()
            if key not in ("rules", "state_digest")}


# ----------------------------------------------------------------------------------------
# Candidate space, image and one-step reach.
# ----------------------------------------------------------------------------------------


def candidate_operators(world: dict[str, Any], space: str) -> list[dict[str, Any]]:
    if space not in CANDIDATE_SPACES:
        raise ValueError("M110 candidate space is outside the authored registry")
    maps = map_space()
    accessors = accessor_operators(world)
    if space == COMPLETE_SPACE:
        return maps + accessors
    monotone_maps = [item for item in maps if map_is_monotone(item)]
    monotone_accessors = [
        item for item in accessors if is_monotone(world, evaluate([item], access_node(item["name"]), world))
    ]
    return monotone_maps + monotone_accessors


_IMAGE_MEMO: dict[tuple[str, str, int], dict[tuple[int, ...], dict[str, Any]]] = {}


def state_image(
    state: dict[str, Any], world: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[tuple[int, ...], dict[str, Any]]:
    """Complete image by node count, with the canonical smallest witness for each value tuple."""
    key = (state["state_digest"], world["world_digest"], max_nodes)
    memo = _IMAGE_MEMO.get(key)
    if memo is not None:
        return memo
    held = {item["name"]: item for item in state["operators"]}
    atoms: dict[tuple[int, ...], dict[str, Any]] = {}
    for field in VISIBLE_FIELDS[: state["interface_width"]]:
        node = field_node(field)
        atoms.setdefault(evaluate(state["operators"], node, world), node)
    for item in state["operators"]:
        if item["kind"] == "access":
            node = access_node(item["name"])
            atoms.setdefault(evaluate(state["operators"], node, world), node)
    maps = [item for item in state["operators"] if item["kind"] == "map"]
    joins = [item for item in state["operators"] if item["kind"] == "binary"]

    by_size: dict[int, dict[tuple[int, ...], dict[str, Any]]] = {1: dict(atoms)}
    found: dict[tuple[int, ...], dict[str, Any]] = dict(atoms)
    for size in range(2, max_nodes + 1):
        level: dict[tuple[int, ...], dict[str, Any]] = {}
        for values, node in by_size.get(size - 1, {}).items():
            for item in maps:
                produced = tuple(item["table"][value] for value in values)
                if produced not in found and produced not in level:
                    level[produced] = map_node(item["name"], node)
        for left_size in range(1, size - 1):
            right_size = size - 1 - left_size
            for left_values, left_node in by_size.get(left_size, {}).items():
                for right_values, right_node in by_size.get(right_size, {}).items():
                    for item in joins:
                        produced = tuple(
                            item["table"][a * len(VALUES) + b]
                            for a, b in zip(left_values, right_values)
                        )
                        if produced not in found and produced not in level:
                            level[produced] = join_node(item["name"], left_node, right_node)
        by_size[size] = level
        found.update(level)
    # Held operators are carried alongside so a witness can be executed without the state.
    _IMAGE_MEMO[key] = found
    del held
    return found


def construct(
    state: dict[str, Any],
    world: dict[str, Any],
    target: Iterable[int],
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    wanted = tuple(int(value) for value in target)
    image = state_image(state, world, max_nodes)
    witness = image.get(wanted)
    report: dict[str, Any] = {
        "target": list(wanted),
        "constructible": witness is not None,
        "image_size": len(image),
        "interface_width": state["interface_width"],
        "candidate_space": state["candidate_space"],
        "witness": witness,
        "witness_nodes": node_count(witness) if witness else None,
        "executes_to_target": False,
        "rendered_python_agrees": False,
    }
    if witness is not None:
        report["executes_to_target"] = evaluate(state["operators"], witness, world) == wanted
        report["rendered_python_agrees"] = (
            execute_rendered(state["operators"], witness, world) == wanted
        )
    return report


_STEP_MEMO: dict[tuple[str, str, int], dict[tuple[int, ...], dict[str, Any]]] = {}


def _one_step_operator_reach(
    state: dict[str, Any], world: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[tuple[int, ...], dict[str, Any]]:
    key = (state["state_digest"], world["world_digest"], max_nodes)
    memo = _STEP_MEMO.get(key)
    if memo is not None:
        return memo
    memo = {}
    for candidate in candidate_operators(world, state["candidate_space"]):
        extended = create_state(
            state["operators"] + [candidate],
            interface_width=state["interface_width"],
            candidate_space=state["candidate_space"],
            rules=state["rules"],
        )
        for values in state_image(extended, world, max_nodes):
            memo.setdefault(values, extended)
    _STEP_MEMO[key] = memo
    return memo


# ----------------------------------------------------------------------------------------
# The three axes.
# ----------------------------------------------------------------------------------------


def extend_operator_table(
    state: dict[str, Any],
    world: dict[str, Any],
    target: Iterable[int],
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    wanted = tuple(int(value) for value in target)
    space = candidate_operators(world, state["candidate_space"])
    extended = _one_step_operator_reach(state, world, max_nodes).get(wanted)
    if extended is not None:
        return {
            "confirmed": True,
            "component": COMPONENT_OPERATORS,
            "candidate_space_size": len(space),
            "candidate_space_exhausted": False,
            "next_state": extended,
        }
    return {
        "confirmed": False,
        "component": COMPONENT_OPERATORS,
        "reason": "candidate_space_exhausted_for_this_demand",
        "candidate_space_size": len(space),
        "candidate_space_exhausted": True,
    }


def extend_signal_interface(state: dict[str, Any]) -> dict[str, Any]:
    width = state["interface_width"] + 1
    if width > MAX_INTERFACE_WIDTH:
        return {
            "confirmed": False,
            "component": COMPONENT_SIGNALS,
            "reason": "signal_interface_ceiling_reached",
        }
    return {
        "confirmed": True,
        "component": COMPONENT_SIGNALS,
        "interface_width": width,
        "next_state": create_state(
            state["operators"],
            interface_width=width,
            candidate_space=state["candidate_space"],
            rules=state["rules"],
        ),
    }


def widen_candidate_space(state: dict[str, Any]) -> dict[str, Any]:
    if state["candidate_space"] == COMPLETE_SPACE:
        return {
            "confirmed": False,
            "component": COMPONENT_CANDIDATES,
            "reason": "candidate_space_ceiling_reached",
        }
    return {
        "confirmed": True,
        "component": COMPONENT_CANDIDATES,
        "candidate_space": COMPLETE_SPACE,
        "next_state": create_state(
            state["operators"],
            interface_width=state["interface_width"],
            candidate_space=COMPLETE_SPACE,
            rules=state["rules"],
        ),
    }


def _widened_then_extended(
    state: dict[str, Any], world: dict[str, Any], target: Iterable[int], max_nodes: int
) -> dict[str, Any] | None:
    widened = widen_candidate_space(state)
    if not widened["confirmed"]:
        return None
    found = extend_operator_table(widened["next_state"], world, target, max_nodes)
    return found["next_state"] if found["confirmed"] else None


# ----------------------------------------------------------------------------------------
# Ground truth in this domain: the consumer's own controlled trial. No rule is consulted.
# ----------------------------------------------------------------------------------------


def component_trial(
    state: dict[str, Any],
    world: dict[str, Any],
    target: Iterable[int],
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """Which single component must be extended for this target to become constructible?

    The same necessity semantics the producer declared, evaluated against this domain's own
    structure. Nothing here reads a rule, so this is an independent ground truth against which a
    restored cascade can be wrong -- and at row 5 it is.
    """
    wanted = tuple(int(value) for value in target)
    outcomes: dict[str, bool] = {}
    outcomes[COMPONENT_OPERATORS] = bool(
        extend_operator_table(state, world, wanted, max_nodes)["confirmed"]
    )
    widened = extend_signal_interface(state)
    outcomes[COMPONENT_SIGNALS] = bool(
        widened["confirmed"]
        and construct(widened["next_state"], world, wanted, max_nodes)["constructible"]
    )
    reached = _widened_then_extended(state, world, wanted, max_nodes)
    outcomes[COMPONENT_CANDIDATES] = bool(reached is not None) and not outcomes[COMPONENT_OPERATORS]
    resolving = sorted(name for name, ok in outcomes.items() if ok)
    return {
        "schema": "m110-component-trial-v1",
        "outcomes": outcomes,
        "resolving_components": resolving,
        "determined": len(resolving) == 1,
        "component": resolving[0] if len(resolving) == 1 else None,
        "label_source": "consumer_component_trial",
        "semantics": "minimal_necessary_component",
        "components_examined": sorted(COMPONENTS),
    }


def failure_features(
    state: dict[str, Any],
    world: dict[str, Any],
    target: Iterable[int],
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """The producer's three features, computed from this domain's structure.

    ``g0`` is the general reading of the producer's ``depends_on_signal``: the target is not a
    function of what the interface can see. In a world whose rows are every signal vector the two
    coincide; here the reference edge lets ``g0`` be true while an operator addition still resolves
    the demand, which is precisely the implication the producer's world enforces and this one does
    not.
    """
    wanted = tuple(int(value) for value in target)
    g0 = not is_function_of_visible(world, wanted, state["interface_width"])
    step = _one_step_operator_reach(state, world, max_nodes)
    g1 = wanted not in step
    g2 = bool(set(step) - set(state_image(state, world, max_nodes)))
    values = (bool(g0), bool(g1), bool(g2))
    return {
        "schema": "m110-failure-features-v1",
        "features": list(FEATURE_NAMES),
        "values": [bool(value) for value in values],
        "row_index": FEATURE_ROWS.index(values),
    }


def attribute(state: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    """Delegated to the producer module unchanged. A reimplementation would end the chain."""
    return lineage.attribute({"rules": state["rules"]}, features)


# ----------------------------------------------------------------------------------------
# Resolution: one machinery step, no trial, identical budget in every arm.
# ----------------------------------------------------------------------------------------


def resolve(
    state: dict[str, Any],
    world: dict[str, Any],
    demand: dict[str, Any],
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    decoded = decode_demand(demand)
    wanted = tuple(decoded["target"])
    current = decode_state(state)
    trace: list[dict[str, Any]] = []
    for step in range(MACHINERY_STEP_BUDGET + 1):
        built = construct(current, world, wanted, max_nodes)
        if built["constructible"]:
            return {
                "schema": "m110-resolution-v1",
                "confirmed": True,
                "steps": step,
                "trace": trace,
                "construction": built,
                "final_interface_width": current["interface_width"],
                "final_candidate_space": current["candidate_space"],
                "final_state_digest": current["state_digest"],
                "trials_performed": 0,
            }
        if step == MACHINERY_STEP_BUDGET:
            break
        features = failure_features(current, world, wanted, max_nodes)
        blame = attribute(current, features)
        if blame["component"] == COMPONENT_SIGNALS:
            extension = extend_signal_interface(current)
        elif blame["component"] == COMPONENT_CANDIDATES:
            widened = widen_candidate_space(current)
            extension = (
                extend_operator_table(widened["next_state"], world, wanted, max_nodes)
                if widened["confirmed"]
                else widened
            )
            if extension.get("confirmed"):
                extension = dict(extension)
                extension["component"] = COMPONENT_CANDIDATES
        else:
            extension = extend_operator_table(current, world, wanted, max_nodes)
        entry = {
            "step": step,
            "features": features,
            "attribution": blame,
            "extension": {k: v for k, v in extension.items() if k != "next_state"},
            "reach_before": built["image_size"],
        }
        if extension.get("confirmed"):
            entry["reach_after"] = len(state_image(extension["next_state"], world, max_nodes))
            entry["reach_strictly_grew"] = entry["reach_after"] > entry["reach_before"]
        trace.append(entry)
        if not extension.get("confirmed"):
            return {
                "schema": "m110-resolution-v1",
                "confirmed": False,
                "reason": extension.get("reason", "extension_refused"),
                "steps": step + 1,
                "trace": trace,
                "construction": built,
                "final_interface_width": current["interface_width"],
                "final_candidate_space": current["candidate_space"],
                "final_state_digest": current["state_digest"],
                "trials_performed": 0,
            }
        current = extension["next_state"]
    final = construct(current, world, wanted, max_nodes)
    return {
        "schema": "m110-resolution-v1",
        "confirmed": bool(final["constructible"]),
        "reason": None if final["constructible"] else "machinery_step_budget_reached",
        "steps": MACHINERY_STEP_BUDGET,
        "trace": trace,
        "construction": final,
        "final_interface_width": current["interface_width"],
        "final_candidate_space": current["candidate_space"],
        "final_state_digest": current["state_digest"],
        "trials_performed": 0,
    }


# ----------------------------------------------------------------------------------------
# Demands, derived from a world by a rule that cannot see the arms.
# ----------------------------------------------------------------------------------------


def consumer_demand(name: str, target: Iterable[int]) -> dict[str, Any]:
    values = [int(item) for item in target]
    if len(values) != DOCUMENT_COUNT or any(item not in VALUES for item in values):
        raise ValueError("M110 demand target is outside the authored value chain")
    payload = {"schema": DEMAND_SCHEMA, "name": str(name), "target": values}
    payload["demand_digest"] = digest(payload)
    return payload


def decode_demand(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != DEMAND_SCHEMA:
        raise ValueError("M110 demand payload is invalid")
    rebuilt = consumer_demand(raw.get("name"), raw.get("target") or [])
    if rebuilt["demand_digest"] != raw.get("demand_digest"):
        raise ValueError("M110 demand identity mismatch")
    return rebuilt


def probe_states() -> list[dict[str, Any]]:
    """Every state the machinery can occupy at the moment it attributes.

    The step budget is one and each demand is posed from the arm's entry state, so an attribution
    never happens at a state holding an acquired operator. Both widths and both candidate spaces are
    censused anyway.
    """
    return [
        create_state(interface_width=width, candidate_space=space)
        for width in (BASE_INTERFACE_WIDTH, MAX_INTERFACE_WIDTH)
        for space in CANDIDATE_SPACES
    ]


def attribution_census(
    world: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """Every feature row that can arise while attributing, over every state and every target."""
    witnesses: dict[int, dict[str, Any]] = {}
    labels: dict[int, set[str]] = {}
    canonical: dict[int, tuple[int, ...]] = {}
    counts: dict[int, int] = {}
    examined = 0
    base = create_state()["state_digest"]
    for state in probe_states():
        image = state_image(state, world, max_nodes)
        for values in itertools.product(VALUES, repeat=DOCUMENT_COUNT):
            if values in image:
                continue
            trial = component_trial(state, world, values, max_nodes)
            if not trial["determined"]:
                continue
            examined += 1
            row = failure_features(state, world, values, max_nodes)["row_index"]
            labels.setdefault(row, set()).add(trial["component"])
            counts[row] = counts.get(row, 0) + 1
            witnesses.setdefault(
                row,
                {
                    "row_index": row,
                    "values": list(FEATURE_ROWS[row]),
                    "interface_width": state["interface_width"],
                    "candidate_space": state["candidate_space"],
                    "component": trial["component"],
                },
            )
            # The canonical demand for a row is the least determined target at the base state.
            if state["state_digest"] == base and (
                row not in canonical or values < canonical[row]
            ):
                canonical[row] = values
    return {
        "schema": "m110-attribution-census-v1",
        "world_id": world["world_id"],
        "world_digest": world["world_digest"],
        "rows": sorted(witnesses),
        "unreachable_rows": [row for row in range(len(FEATURE_ROWS)) if row not in witnesses],
        "ambiguous_rows": sorted(row for row, found in labels.items() if len(found) > 1),
        "row_labels": {str(row): sorted(found) for row, found in sorted(labels.items())},
        "row_counts": {str(row): counts[row] for row in sorted(counts)},
        "canonical_targets": {str(row): list(canonical[row]) for row in sorted(canonical)},
        "determined_pairs_examined": examined,
        "state_family_size": len(probe_states()),
        "target_space_size": len(VALUES) ** DOCUMENT_COUNT,
        "census_complete": True,
        "witnesses": [witnesses[row] for row in sorted(witnesses)],
    }


# ----------------------------------------------------------------------------------------
# Certificates: the three lemmas that make refusal a reach fact rather than a budget fact.
# ----------------------------------------------------------------------------------------


def monotone_closure_certificate(
    state: dict[str, Any], world: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    candidates = candidate_operators(world, MONOTONE_SPACE)
    reachable = set(state_image(state, world, max_nodes))
    for candidate in candidates:
        extended = create_state(
            state["operators"] + [candidate],
            interface_width=state["interface_width"],
            candidate_space=MONOTONE_SPACE,
            rules=state["rules"],
        )
        reachable |= set(state_image(extended, world, max_nodes))
    held_monotone = all(
        is_monotone(world, evaluate(state["operators"], node, world))
        for node in _atom_nodes(state, world)
    )
    certificate = {
        "schema": "m110-monotone-closure-v1",
        "space": MONOTONE_SPACE,
        "interface_width": state["interface_width"],
        "max_nodes": max_nodes,
        "candidate_count": len(candidates),
        "reachable_count": len(reachable),
        "every_held_atom_is_monotone": bool(held_monotone),
        "every_candidate_map_is_monotone": all(
            map_is_monotone(item) for item in candidates if item["kind"] == "map"
        ),
        "every_candidate_accessor_is_monotone": all(
            is_monotone(world, evaluate([item], access_node(item["name"]), world))
            for item in candidates
            if item["kind"] == "access"
        ),
        "everything_reachable_is_monotone": all(
            is_monotone(world, values) for values in reachable
        ),
    }
    certificate["closed_by_monotone_lemma"] = bool(
        certificate["every_held_atom_is_monotone"]
        and certificate["every_candidate_map_is_monotone"]
        and certificate["every_candidate_accessor_is_monotone"]
        and certificate["everything_reachable_is_monotone"]
    )
    certificate["budget_independent"] = certificate["closed_by_monotone_lemma"]
    certificate["confirmed"] = certificate["closed_by_monotone_lemma"]
    return certificate


def _atom_nodes(state: dict[str, Any], world: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [field_node(field) for field in VISIBLE_FIELDS[: state["interface_width"]]]
    nodes += [access_node(item["name"]) for item in state["operators"] if item["kind"] == "access"]
    return nodes


def visible_function_certificate(
    world: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """No expression over an accessor-free state can produce a target the interface cannot separate."""
    measured = {}
    for width in range(1, MAX_INTERFACE_WIDTH + 1):
        state = create_state(interface_width=width)
        image = state_image(state, world, max_nodes)
        measured[str(width)] = sum(
            0 if is_function_of_visible(world, values, width) else 1 for values in image
        )
    certificate = {
        "schema": "m110-visible-function-v1",
        "max_nodes": max_nodes,
        "violations_by_width": measured,
        "widths_examined": sorted(measured),
    }
    certificate["confirmed"] = all(value == 0 for value in measured.values())
    return certificate


def fixed_point_certificate(world: dict[str, Any]) -> dict[str, Any]:
    """The declared bound records closure, not a search budget."""
    sizes: dict[str, dict[str, int]] = {}
    for state in probe_states():
        key = "%d-%s" % (state["interface_width"], state["candidate_space"])
        sizes[key] = {
            str(bound): len(state_image(state, world, bound)) for bound in FIXED_POINT_BOUNDS
        }
    certificate = {
        "schema": "m110-fixed-point-v1",
        "bounds": list(FIXED_POINT_BOUNDS),
        "image_sizes": sizes,
    }
    certificate["confirmed"] = all(len(set(entry.values())) == 1 for entry in sizes.values())
    return certificate


def reach_improve(
    state: dict[str, Any], world: dict[str, Any], budget: int = 2,
    max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """Every target the machinery can get the lineage to construct, over the axes it can name."""
    axes = {rule["selects_component_when_true"] for rule in state["rules"]}
    axes.add(COMPONENT_OPERATORS)
    reached: set[tuple[int, ...]] = set(state_image(state, world, max_nodes))
    frontier = [state]
    for _ in range(budget):
        produced: dict[str, dict[str, Any]] = {}
        for item in frontier:
            options: list[dict[str, Any]] = []
            if COMPONENT_SIGNALS in axes:
                options.append(extend_signal_interface(item))
            if COMPONENT_CANDIDATES in axes:
                options.append(widen_candidate_space(item))
            for candidate in candidate_operators(world, item["candidate_space"]):
                options.append(
                    {
                        "confirmed": True,
                        "next_state": create_state(
                            item["operators"] + [candidate],
                            interface_width=item["interface_width"],
                            candidate_space=item["candidate_space"],
                            rules=item["rules"],
                        ),
                    }
                )
            for option in options:
                if not option.get("confirmed"):
                    continue
                following = option["next_state"]
                reached |= set(state_image(following, world, max_nodes))
                produced.setdefault(following["state_digest"], following)
        frontier = list(produced.values())
    return {
        "schema": "m110-reach-improve-v1",
        "budget": budget,
        "axes": sorted(axes),
        "size": len(reached),
        "digest": digest(sorted("".join(str(value) for value in item) for item in reached)),
        "tables": sorted("".join(str(value) for value in item) for item in reached),
    }
