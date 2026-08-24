"""Bounded M105 executable constructor-vocabulary runtime.

M105 embeds the exact positive M104 V3 state byte-for-byte.  Its new state-owned
registry may hold one content-addressed executable Boolean feature learned from
DEVELOPMENT behavior.  Later JSON-document and SQLite definitions resolve that
feature live.  The lower Boolean interpreter, its two-signal interface, the
eight-node bound, carrier adapters, tasks, and evaluator remain authored.

The module grants no repository, network, credential, deployment, evaluator-
changing, or permission-changing authority.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import itertools
import json
import platform
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

try:  # The file must also run inside an isolated copied capsule.
    from . import m103_runtime
except ImportError:  # pragma: no cover - exercised by capsule tests
    import m103_runtime  # type: ignore[no-redef]


STATE_SCHEMA = "m105-lineage-state-v1"
FEATURE_SCHEMA = "m105-constructor-feature-v1"
FEATURE_DEMAND_SCHEMA = "m105-feature-demand-v1"
CONSUMER_DEMAND_SCHEMA = "m105-consumer-demand-v1"
ACTION_SCHEMA = "m105-action-v1"
DEFINITION_SCHEMA = "m105-consumer-definition-v1"

M104_V3_RAW_SHA256 = "98d61df076e6b764f6b00f27793b82ef27e20cd35049780499029dc3ed7edf77"
M104_V3_STATE_DIGEST = "a34b3b9dab99ee848a9c209a95ec9201fd7056eb99393d45d4041c885f19417a"
M104_V3_LENGTH = 8011
M104_CONSTRUCTOR_ID = "constructor-s-prime-44b6c4c7f1bbe12c"
M104_DEFINITION_IDS = (
    "consumer-a3fc0657cb475d16",
    "consumer-a687ff8014d8b314",
)

MAX_EXPRESSION_NODES = 8
SIGNAL_ROWS = ((False, False), (False, True), (True, False), (True, True))
SUPPORTED_FAMILIES = {"json_document", "sqlite"}
_SAFE_TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


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


def _safe_token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_TOKEN.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _expression_node_count(expression: dict[str, Any]) -> int:
    op = expression["op"]
    if op in {"CONST", "INPUT"}:
        return 1
    if op == "NOT":
        return 1 + _expression_node_count(expression["child"])
    return 1 + _expression_node_count(expression["left"]) + _expression_node_count(
        expression["right"]
    )


def const(value: bool) -> dict[str, Any]:
    if not isinstance(value, bool):
        raise ValueError("Boolean constant is invalid")
    return {"op": "CONST", "value": value}


def signal(index: int) -> dict[str, Any]:
    if index not in {0, 1}:
        raise ValueError("Boolean input index is invalid")
    return {"op": "INPUT", "index": index}


def negate(child: dict[str, Any]) -> dict[str, Any]:
    return {"op": "NOT", "child": decode_expression(child)}


def combine(op: str, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    if op not in {"AND", "OR"}:
        raise ValueError("Boolean binary operator is invalid")
    children = sorted([decode_expression(left), decode_expression(right)], key=canonical_json)
    return {"op": op, "left": children[0], "right": children[1]}


def decode_expression(raw: Any, *, enforce_bound: bool = True) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("op"), str):
        raise ValueError("M105 expression is invalid")
    op = raw["op"]
    if op == "CONST":
        item = _closed(copy.deepcopy(raw), {"op", "value"}, "M105 constant")
        if not isinstance(item["value"], bool):
            raise ValueError("M105 constant value is invalid")
    elif op == "INPUT":
        item = _closed(copy.deepcopy(raw), {"op", "index"}, "M105 input")
        if item["index"] not in {0, 1}:
            raise ValueError("M105 input index is invalid")
    elif op == "NOT":
        item = _closed(copy.deepcopy(raw), {"op", "child"}, "M105 negation")
        item["child"] = decode_expression(item["child"], enforce_bound=False)
    elif op in {"AND", "OR"}:
        item = _closed(copy.deepcopy(raw), {"op", "left", "right"}, "M105 binary")
        item["left"] = decode_expression(item["left"], enforce_bound=False)
        item["right"] = decode_expression(item["right"], enforce_bound=False)
        if canonical_json(item["left"]) > canonical_json(item["right"]):
            raise ValueError("M105 commutative children are not canonical")
    else:
        raise ValueError("M105 expression operator is invalid")
    if enforce_bound and _expression_node_count(item) > MAX_EXPRESSION_NODES:
        raise ValueError("M105 expression exceeds the node bound")
    return item


def execute_expression(expression: dict[str, Any], signals: Iterable[bool]) -> bool:
    body = decode_expression(expression)
    values = tuple(signals)
    if len(values) != 2 or not all(isinstance(value, bool) for value in values):
        raise ValueError("M105 signals must contain exactly two Booleans")

    def run(node: dict[str, Any]) -> bool:
        op = node["op"]
        if op == "CONST":
            return node["value"]
        if op == "INPUT":
            return values[node["index"]]
        if op == "NOT":
            return not run(node["child"])
        if op == "AND":
            return run(node["left"]) and run(node["right"])
        return run(node["left"]) or run(node["right"])

    return run(body)


def expression_truth_table(expression: dict[str, Any]) -> tuple[bool, bool, bool, bool]:
    return tuple(execute_expression(expression, row) for row in SIGNAL_ROWS)  # type: ignore[return-value]


@functools.lru_cache(maxsize=1)
def _enumerated_semantic_items() -> tuple[
    tuple[tuple[bool, bool, bool, bool], str], ...
]:
    """Cache immutable canonical representatives; callers receive fresh objects."""

    seeds = [const(False), const(True), signal(0), signal(1)]
    by_size: dict[int, list[dict[str, Any]]] = {1: seeds}
    representatives: dict[tuple[bool, bool, bool, bool], dict[str, Any]] = {
        expression_truth_table(candidate): candidate for candidate in seeds
    }
    for size in range(2, MAX_EXPRESSION_NODES + 1):
        candidates: dict[str, dict[str, Any]] = {}
        for child in by_size.get(size - 1, []):
            node = negate(child)
            candidates[canonical_json(node)] = node
        for left_size in range(1, size - 1):
            right_size = size - 1 - left_size
            for left in by_size.get(left_size, []):
                for right in by_size.get(right_size, []):
                    for op in ("AND", "OR"):
                        node = combine(op, left, right)
                        candidates[canonical_json(node)] = node
        # An optimal expression contains optimal subexpressions.  Keeping only
        # one canonical shortest representative per already discovered
        # semantic therefore preserves the complete shortest-expression image.
        newly_discovered: dict[tuple[bool, bool, bool, bool], dict[str, Any]] = {}
        for key in sorted(candidates):
            candidate = candidates[key]
            table = expression_truth_table(candidate)
            if table not in representatives and table not in newly_discovered:
                newly_discovered[table] = candidate
        by_size[size] = list(newly_discovered.values())
        representatives.update(newly_discovered)

    return tuple(
        (table, canonical_json(body))
        for table, body in sorted(representatives.items(), key=lambda item: item[0])
    )


def enumerate_boolean_semantics() -> dict[tuple[bool, bool, bool, bool], dict[str, Any]]:
    """Return the canonical shortest representative of every <=8-node semantic."""

    return {table: json.loads(body) for table, body in _enumerated_semantic_items()}


def semantic_census() -> dict[str, Any]:
    representatives = enumerate_boolean_semantics()
    counts: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for table, body in representatives.items():
        nodes = _expression_node_count(body)
        counts[str(nodes)] = counts.get(str(nodes), 0) + 1
        rows.append({"truth_table": list(table), "nodes": nodes, "body": body})
    report = {
        "schema": "m105-semantic-census-v1",
        "maximum_nodes": MAX_EXPRESSION_NODES,
        "semantic_count": len(rows),
        "counts_by_shortest_size": counts,
        "representatives": rows,
        "complete_two_input_boolean_image": len(rows) == 16,
    }
    report["census_digest"] = digest(report)
    return report


def feature_definition(body: dict[str, Any]) -> dict[str, Any]:
    body = decode_expression(body)
    payload = {
        "schema": FEATURE_SCHEMA,
        "body": body,
        "truth_table": list(expression_truth_table(body)),
    }
    return {"feature_id": f"feature-{digest(payload)[:16]}", **payload}


def decode_feature(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw), {"schema", "feature_id", "body", "truth_table"}, "M105 feature"
    )
    if item["schema"] != FEATURE_SCHEMA:
        raise ValueError("M105 feature schema mismatch")
    expected = feature_definition(item["body"])
    if item != expected:
        raise ValueError("M105 feature content address or truth table mismatch")
    return item


def _signals(value: Any, label: str) -> list[bool]:
    if not isinstance(value, list) or len(value) != 2 or not all(
        isinstance(item, bool) for item in value
    ):
        raise ValueError(f"{label} signals are invalid")
    return list(value)


def _nonce(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 200:
        raise ValueError(f"{label} nonce is invalid")
    return value


def feature_demand(demand_id: str, observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return decode_feature_demand(
        {
            "schema": FEATURE_DEMAND_SCHEMA,
            "demand_id": demand_id,
            "observations": list(observations),
        }
    )


def decode_feature_demand(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw), {"schema", "demand_id", "observations"}, "M105 feature demand"
    )
    if item["schema"] != FEATURE_DEMAND_SCHEMA:
        raise ValueError("M105 feature demand schema mismatch")
    _safe_token(item["demand_id"], "M105 feature demand id")
    if not isinstance(item["observations"], list) or not item["observations"]:
        raise ValueError("M105 feature observations are missing")
    observations: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for raw_observation in item["observations"]:
        observation = _closed(
            copy.deepcopy(raw_observation),
            {"case_id", "signals", "nonce", "expected"},
            "M105 feature observation",
        )
        identifier = _safe_token(observation["case_id"], "M105 feature case id")
        if identifier in identifiers:
            raise ValueError("M105 feature case id is duplicated")
        identifiers.add(identifier)
        observation["signals"] = _signals(observation["signals"], "M105 feature")
        observation["nonce"] = _nonce(observation["nonce"], "M105 feature")
        if not isinstance(observation["expected"], bool):
            raise ValueError("M105 feature expected class is invalid")
        observations.append(observation)
    item["observations"] = observations
    return item


def action_definition(descriptor: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(descriptor, dict) or not isinstance(descriptor.get("kind"), str):
        raise ValueError("M105 action descriptor is invalid")
    payload = {"schema": ACTION_SCHEMA, "descriptor": copy.deepcopy(descriptor)}
    return {"action_id": f"action-{digest(payload)[:16]}", **payload}


def decode_action(raw: Any) -> dict[str, Any]:
    item = _closed(copy.deepcopy(raw), {"schema", "action_id", "descriptor"}, "M105 action")
    if item["schema"] != ACTION_SCHEMA or not isinstance(item["descriptor"], dict):
        raise ValueError("M105 action schema/descriptor is invalid")
    if item != action_definition(item["descriptor"]):
        raise ValueError("M105 action content address mismatch")
    return item


def _context(value: Any, label: str) -> dict[str, Any]:
    item = _closed(copy.deepcopy(value), {"signals", "nonce"}, f"{label} context")
    item["signals"] = _signals(item["signals"], label)
    item["nonce"] = _nonce(item["nonce"], label)
    return item


def _consumer_cases(value: Any, *, expected: bool, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} are missing")
    keys = {"case_id", "context", "initial", "expected"} if expected else {
        "probe_id",
        "context",
        "initial",
    }
    id_key = "case_id" if expected else "probe_id"
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for raw_case in value:
        case = _closed(copy.deepcopy(raw_case), keys, f"M105 {label} item")
        identifier = _safe_token(case[id_key], f"M105 {label} id")
        if identifier in seen:
            raise ValueError(f"M105 {label} id is duplicated")
        seen.add(identifier)
        case["context"] = _context(case["context"], f"M105 {label}")
        canonical_json(case["initial"])
        if expected:
            canonical_json(case["expected"])
        output.append(case)
    return output


def consumer_demand(
    demand_id: str,
    family: str,
    actions: Iterable[dict[str, Any]],
    public_cases: Iterable[dict[str, Any]],
    diagnostic_probes: Iterable[dict[str, Any]],
    *,
    max_trace: int,
) -> dict[str, Any]:
    return decode_consumer_demand(
        {
            "schema": CONSUMER_DEMAND_SCHEMA,
            "demand_id": demand_id,
            "family": family,
            "actions": list(actions),
            "public_cases": list(public_cases),
            "diagnostic_probes": list(diagnostic_probes),
            "max_trace": max_trace,
        }
    )


def decode_consumer_demand(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {
            "schema",
            "demand_id",
            "family",
            "actions",
            "public_cases",
            "diagnostic_probes",
            "max_trace",
        },
        "M105 consumer demand",
    )
    if item["schema"] != CONSUMER_DEMAND_SCHEMA:
        raise ValueError("M105 consumer demand schema mismatch")
    _safe_token(item["demand_id"], "M105 consumer demand id")
    if item["family"] not in SUPPORTED_FAMILIES:
        raise ValueError("M105 consumer family is invalid")
    if not isinstance(item["actions"], list) or not item["actions"]:
        raise ValueError("M105 consumer actions are missing")
    item["actions"] = [decode_action(action) for action in item["actions"]]
    action_ids = [action["action_id"] for action in item["actions"]]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("M105 consumer action is duplicated")
    item["public_cases"] = _consumer_cases(
        item["public_cases"], expected=True, label="public cases"
    )
    item["diagnostic_probes"] = _consumer_cases(
        item["diagnostic_probes"], expected=False, label="diagnostic probes"
    )
    if not isinstance(item["max_trace"], int) or not 1 <= item["max_trace"] <= 2:
        raise ValueError("M105 consumer trace bound is invalid")
    return item


def _definition_id(payload: dict[str, Any]) -> str:
    return f"consumer-{digest(payload)[:16]}"


def consumer_definition(
    family: str,
    feature_id: str,
    actions: list[dict[str, Any]],
    false_body: list[str],
    true_body: list[str],
) -> dict[str, Any]:
    payload = {
        "schema": DEFINITION_SCHEMA,
        "family": family,
        "feature_id": feature_id,
        "actions": copy.deepcopy(actions),
        "branches": {"false": list(false_body), "true": list(true_body)},
    }
    return {"definition_id": _definition_id(payload), **payload}


def decode_definition(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {"schema", "definition_id", "family", "feature_id", "actions", "branches"},
        "M105 consumer definition",
    )
    if item["schema"] != DEFINITION_SCHEMA or item["family"] not in SUPPORTED_FAMILIES:
        raise ValueError("M105 consumer schema/family mismatch")
    if not isinstance(item["feature_id"], str) or not item["feature_id"]:
        raise ValueError("M105 consumer feature dependency is invalid")
    if not isinstance(item["actions"], list) or not item["actions"]:
        raise ValueError("M105 consumer actions are missing")
    item["actions"] = [decode_action(action) for action in item["actions"]]
    action_ids = {action["action_id"] for action in item["actions"]}
    branches = _closed(copy.deepcopy(item["branches"]), {"false", "true"}, "M105 branches")
    for branch in ("false", "true"):
        body = branches[branch]
        if not isinstance(body, list) or not 1 <= len(body) <= 2:
            raise ValueError("M105 consumer branch is invalid")
        if not all(isinstance(action_id, str) and action_id in action_ids for action_id in body):
            raise ValueError("M105 consumer branch references an absent action")
    item["branches"] = branches
    payload = {key: value for key, value in item.items() if key != "definition_id"}
    if item["definition_id"] != _definition_id(payload):
        raise ValueError("M105 consumer content address mismatch")
    return item


def _state(
    m104_bytes: bytes,
    features: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "schema": STATE_SCHEMA,
        "m104_sha256": sha256_bytes(m104_bytes),
        "m104_ascii": m104_bytes.decode("ascii"),
        "features": copy.deepcopy(features),
        "definitions": copy.deepcopy(definitions),
    }
    payload["state_digest"] = digest(payload)
    return payload


def _validate_exact_m104(m104_bytes: bytes) -> dict[str, Any]:
    if len(m104_bytes) != M104_V3_LENGTH or sha256_bytes(m104_bytes) != M104_V3_RAW_SHA256:
        raise ValueError("M105 requires the exact positive M104 V3 bytes")
    predecessor = m103_runtime.decode_state(m104_bytes)
    if predecessor["state_digest"] != M104_V3_STATE_DIGEST:
        raise ValueError("M105 predecessor state digest mismatch")
    if predecessor["constructor"]["constructor_id"] != M104_CONSTRUCTOR_ID:
        raise ValueError("M105 predecessor constructor mismatch")
    if tuple(item["definition_id"] for item in predecessor["definitions"]) != M104_DEFINITION_IDS:
        raise ValueError("M105 predecessor definitions mismatch")
    return predecessor


def create_state(m104_bytes: bytes) -> dict[str, Any]:
    _validate_exact_m104(m104_bytes)
    return decode_state(_state(m104_bytes, [], []))


def decode_state(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        value = copy.deepcopy(raw)
    else:
        raw_bytes = raw.encode("ascii") if isinstance(raw, str) else raw
        try:
            value = json.loads(raw_bytes.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"M105 state is not canonical ASCII JSON: {error}") from error
        if canonical_json(value).encode("ascii") != raw_bytes:
            raise ValueError("M105 state bytes are not canonical JSON")
    value = _closed(
        value,
        {"schema", "m104_sha256", "m104_ascii", "features", "definitions", "state_digest"},
        "M105 state",
    )
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    if value["schema"] != STATE_SCHEMA or value["state_digest"] != digest(payload):
        raise ValueError("M105 state schema or digest mismatch")
    if not isinstance(value["m104_ascii"], str) or not isinstance(value["m104_sha256"], str):
        raise ValueError("M105 predecessor binding is invalid")
    m104_bytes = value["m104_ascii"].encode("ascii")
    if sha256_bytes(m104_bytes) != value["m104_sha256"]:
        raise ValueError("M105 embedded M104 bytes changed")
    _validate_exact_m104(m104_bytes)
    if not isinstance(value["features"], list) or len(value["features"]) > 1:
        raise ValueError("M105 feature registry is invalid")
    value["features"] = [decode_feature(feature) for feature in value["features"]]
    feature_ids = {feature["feature_id"] for feature in value["features"]}
    if not isinstance(value["definitions"], list):
        raise ValueError("M105 definitions are invalid")
    value["definitions"] = [decode_definition(definition) for definition in value["definitions"]]
    definition_ids = [definition["definition_id"] for definition in value["definitions"]]
    if len(definition_ids) != len(set(definition_ids)):
        raise ValueError("M105 state contains duplicate definitions")
    families = [definition["family"] for definition in value["definitions"]]
    if len(families) != len(set(families)):
        raise ValueError("M105 state contains duplicate consumer families")
    if any(definition["feature_id"] not in feature_ids for definition in value["definitions"]):
        raise ValueError("M105 live feature dependency is missing")
    return value


def encode_state(state: dict[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


def _next_state(
    state: dict[str, Any],
    *,
    features: list[dict[str, Any]] | None = None,
    definitions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    state = decode_state(state)
    return decode_state(
        _state(
            state["m104_ascii"].encode("ascii"),
            state["features"] if features is None else features,
            state["definitions"] if definitions is None else definitions,
        )
    )


def acquire_feature(
    state: dict[str, Any], demand: dict[str, Any], *, register_result: bool
) -> dict[str, Any]:
    state = decode_state(state)
    demand = decode_feature_demand(demand)
    if state["features"]:
        return {
            "schema": "m105-feature-acquisition-v1",
            "confirmed": False,
            "registered": False,
            "reason": "feature_registry_not_empty",
            "next_state": None,
        }
    representatives = enumerate_boolean_semantics()
    accepted: list[tuple[tuple[bool, bool, bool, bool], dict[str, Any]]] = []
    for table, body in representatives.items():
        if all(execute_expression(body, observation["signals"]) == observation["expected"] for observation in demand["observations"]):
            accepted.append((table, body))
    all_signal_pairs = {tuple(observation["signals"]) for observation in demand["observations"]}
    nonce_invariance = all(
        len({observation["nonce"] for observation in demand["observations"] if tuple(observation["signals"]) == row}) >= 2
        for row in SIGNAL_ROWS
    )
    confirmed = len(accepted) == 1 and all_signal_pairs == set(SIGNAL_ROWS) and nonce_invariance
    feature = feature_definition(accepted[0][1]) if confirmed else None
    next_state = (
        _next_state(state, features=[feature]) if confirmed and register_result and feature else None
    )
    return {
        "schema": "m105-feature-acquisition-v1",
        "confirmed": confirmed,
        "registered": bool(next_state),
        "reason": "unique_complete_behavior" if confirmed else "ambiguous_or_incomplete_behavior",
        "semantic_image_exhausted": len(representatives) == 16,
        "enumerated_semantics": len(representatives),
        "accepted_semantic_classes": len(accepted),
        "all_signal_pairs_observed": all_signal_pairs == set(SIGNAL_ROWS),
        "nonce_invariance_observed": nonce_invariance,
        "feature": feature,
        "next_state": next_state,
    }


def _json_execute(descriptors: list[dict[str, Any]], initial: Any) -> dict[str, Any]:
    if not isinstance(initial, dict):
        raise ValueError("JSON-document initial state is invalid")
    output = copy.deepcopy(initial)
    for descriptor in descriptors:
        kind = descriptor.get("kind")
        if kind == "set_field":
            key = _safe_token(descriptor.get("key"), "JSON field")
            output[key] = copy.deepcopy(descriptor.get("value"))
        elif kind == "drop_field":
            key = _safe_token(descriptor.get("key"), "JSON field")
            output.pop(key, None)
        elif kind == "rename_field":
            old = _safe_token(descriptor.get("old"), "JSON old field")
            new = _safe_token(descriptor.get("new"), "JSON new field")
            if old in output:
                output[new] = output.pop(old)
        else:
            raise ValueError("Unknown JSON-document action")
    return output


def _sqlite_initial(connection: sqlite3.Connection, initial: Any) -> None:
    item = _closed(copy.deepcopy(initial), {"rows"}, "SQLite initial state")
    if not isinstance(item["rows"], list):
        raise ValueError("SQLite rows are invalid")
    connection.execute(
        "CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT NOT NULL, status TEXT NOT NULL)"
    )
    for raw_row in item["rows"]:
        row = _closed(copy.deepcopy(raw_row), {"id", "value", "status"}, "SQLite row")
        if not isinstance(row["id"], int) or isinstance(row["id"], bool):
            raise ValueError("SQLite row id is invalid")
        if not isinstance(row["value"], str) or not isinstance(row["status"], str):
            raise ValueError("SQLite row text is invalid")
        connection.execute(
            "INSERT INTO records(id, value, status) VALUES (?, ?, ?)",
            (row["id"], row["value"], row["status"]),
        )


def _sqlite_execute(descriptors: list[dict[str, Any]], initial: Any) -> dict[str, Any]:
    connection = sqlite3.connect(":memory:")
    try:
        _sqlite_initial(connection, initial)
        for descriptor in descriptors:
            kind = descriptor.get("kind")
            identifier = descriptor.get("id")
            if not isinstance(identifier, int) or isinstance(identifier, bool):
                raise ValueError("SQLite action id is invalid")
            if kind == "set_status" and isinstance(descriptor.get("status"), str):
                connection.execute(
                    "UPDATE records SET status = ? WHERE id = ?",
                    (descriptor["status"], identifier),
                )
            elif kind == "set_value" and isinstance(descriptor.get("value"), str):
                connection.execute(
                    "UPDATE records SET value = ? WHERE id = ?",
                    (descriptor["value"], identifier),
                )
            elif kind == "delete_id":
                connection.execute("DELETE FROM records WHERE id = ?", (identifier,))
            else:
                raise ValueError("Unknown SQLite action")
        rows = [
            {"id": row[0], "value": row[1], "status": row[2]}
            for row in connection.execute(
                "SELECT id, value, status FROM records ORDER BY id"
            ).fetchall()
        ]
        return {"rows": rows}
    finally:
        connection.close()


def _execute_trace(family: str, actions: list[dict[str, Any]], body: tuple[str, ...] | list[str], initial: Any) -> Any:
    catalogue = {action["action_id"]: action["descriptor"] for action in actions}
    descriptors = [catalogue[action_id] for action_id in body]
    if family == "json_document":
        return _json_execute(descriptors, initial)
    if family == "sqlite":
        return _sqlite_execute(descriptors, initial)
    raise ValueError("M105 carrier family is invalid")


def _trace_candidates(demand: dict[str, Any]) -> list[tuple[str, ...]]:
    action_ids = [action["action_id"] for action in demand["actions"]]
    return [
        body
        for length in range(1, demand["max_trace"] + 1)
        for body in itertools.product(action_ids, repeat=length)
    ]


def _consumer_candidates(
    demand: dict[str, Any], feature: dict[str, Any]
) -> list[dict[str, Any]]:
    traces = _trace_candidates(demand)
    output: list[dict[str, Any]] = []
    for false_body in traces:
        for true_body in traces:
            valid = True
            for case in demand["public_cases"]:
                branch = execute_expression(feature["body"], case["context"]["signals"])
                body = true_body if branch else false_body
                try:
                    actual = _execute_trace(demand["family"], demand["actions"], body, case["initial"])
                except Exception:
                    valid = False
                    break
                if actual != case["expected"]:
                    valid = False
                    break
            if not valid:
                continue
            signature: list[Any] = []
            for probe in demand["diagnostic_probes"]:
                branch = execute_expression(feature["body"], probe["context"]["signals"])
                body = true_body if branch else false_body
                try:
                    signature.append(
                        _execute_trace(demand["family"], demand["actions"], body, probe["initial"])
                    )
                except Exception as error:
                    signature.append({"error": type(error).__name__})
            output.append(
                {
                    "feature": feature,
                    "false_body": list(false_body),
                    "true_body": list(true_body),
                    "signature": signature,
                }
            )
    return output


def acquire_consumer(
    state: dict[str, Any], demand: dict[str, Any], *, register_result: bool
) -> dict[str, Any]:
    state = decode_state(state)
    demand = decode_consumer_demand(demand)
    if any(definition["family"] == demand["family"] for definition in state["definitions"]):
        return {
            "schema": "m105-consumer-acquisition-v1",
            "confirmed": False,
            "registered": False,
            "reason": "consumer_family_already_registered",
            "next_state": None,
        }

    registered_feature = state["features"][0] if state["features"] else None
    candidate_features = (
        [registered_feature]
        if registered_feature is not None
        else [feature_definition(body) for body in enumerate_boolean_semantics().values()]
    )
    candidates: list[dict[str, Any]] = []
    for feature in candidate_features:
        candidates.extend(_consumer_candidates(demand, feature))
    by_signature: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_signature.setdefault(canonical_json(candidate["signature"]), []).append(candidate)
    semantic_classes = len(by_signature)

    if registered_feature is None:
        return {
            "schema": "m105-consumer-acquisition-v1",
            "confirmed": False,
            "registered": False,
            "reason": "ambiguous_public_semantics" if semantic_classes != 1 else "historical_feature_absent",
            "semantic_image_exhausted": len(candidate_features) == 16,
            "enumerated_feature_semantics": len(candidate_features),
            "candidate_count": len(candidates),
            "semantic_classes": semantic_classes,
            "next_state": None,
        }

    if semantic_classes != 1 or not candidates:
        return {
            "schema": "m105-consumer-acquisition-v1",
            "confirmed": False,
            "registered": False,
            "reason": "ambiguous_public_semantics" if candidates else "no_valid_definition",
            "semantic_image_exhausted": True,
            "enumerated_feature_semantics": 1,
            "candidate_count": len(candidates),
            "semantic_classes": semantic_classes,
            "next_state": None,
        }

    selected = min(
        candidates,
        key=lambda item: canonical_json(
            {"false": item["false_body"], "true": item["true_body"]}
        ),
    )
    definition = consumer_definition(
        demand["family"],
        registered_feature["feature_id"],
        demand["actions"],
        selected["false_body"],
        selected["true_body"],
    )
    next_state = (
        _next_state(state, definitions=[*state["definitions"], definition])
        if register_result
        else None
    )
    return {
        "schema": "m105-consumer-acquisition-v1",
        "confirmed": True,
        "registered": bool(next_state),
        "reason": "unique_state_conditioned_behavior",
        "semantic_image_exhausted": True,
        "enumerated_feature_semantics": 1,
        "candidate_count": len(candidates),
        "semantic_classes": semantic_classes,
        "definition": definition,
        "next_state": next_state,
    }


def definition_for_family(state: dict[str, Any], family: str) -> dict[str, Any]:
    state = decode_state(state)
    matches = [definition for definition in state["definitions"] if definition["family"] == family]
    if len(matches) != 1:
        raise ValueError("M105 consumer definition is missing or ambiguous")
    return matches[0]


def execute_definition(
    state: dict[str, Any],
    definition: dict[str, Any] | str,
    context: dict[str, Any],
    initial: Any,
) -> Any:
    state = decode_state(state)
    selected = (
        next(
            (item for item in state["definitions"] if item["definition_id"] == definition),
            None,
        )
        if isinstance(definition, str)
        else decode_definition(definition)
    )
    if selected is None or selected not in state["definitions"]:
        raise ValueError("M105 definition is not registered in the live state")
    features = {
        feature["feature_id"]: feature for feature in state["features"]
    }
    feature = features.get(selected["feature_id"])
    if feature is None:
        raise ValueError("M105 live feature dependency is missing")
    admitted_context = _context(context, "M105 execution")
    branch = execute_expression(feature["body"], admitted_context["signals"])
    body = selected["branches"]["true" if branch else "false"]
    return _execute_trace(selected["family"], selected["actions"], body, initial)


def mutate_feature_and_rebind(state: dict[str, Any]) -> dict[str, Any]:
    state = decode_state(state)
    if len(state["features"]) != 1:
        raise ValueError("M105 semantic mutation requires one live feature")
    current = state["features"][0]
    complement = tuple(not value for value in current["truth_table"])
    body = enumerate_boolean_semantics().get(complement)
    if body is None:
        raise ValueError("M105 semantic complement is outside the complete image")
    mutated = feature_definition(body)
    definitions = [
        consumer_definition(
            definition["family"],
            mutated["feature_id"],
            definition["actions"],
            definition["branches"]["false"],
            definition["branches"]["true"],
        )
        for definition in state["definitions"]
    ]
    return _next_state(state, features=[mutated], definitions=definitions)


def remove_feature_without_rebinding(state: dict[str, Any]) -> dict[str, Any]:
    state = decode_state(state)
    raw = _state(state["m104_ascii"].encode("ascii"), [], state["definitions"])
    return raw


def corrupt_state_digest(state: dict[str, Any]) -> dict[str, Any]:
    raw = copy.deepcopy(decode_state(state))
    raw["state_digest"] = "0" * 64
    return raw


def predecessor_conservation(state: dict[str, Any]) -> dict[str, Any]:
    state = decode_state(state)
    predecessor = m103_runtime.decode_state(state["m104_ascii"].encode("ascii"))
    inherited = m103_runtime.predecessor_conservation(predecessor)
    report = {
        "schema": "m105-predecessor-conservation-v1",
        "m104_raw_sha256": state["m104_sha256"],
        "m104_state_digest": predecessor["state_digest"],
        "m104_constructor_live": predecessor["constructor"]["constructor_id"] == M104_CONSTRUCTOR_ID,
        "m104_definitions_live": tuple(
            definition["definition_id"] for definition in predecessor["definitions"]
        )
        == M104_DEFINITION_IDS,
        "m100_live": inherited["m100_live"],
        "m101_a_live": inherited["m101_a_live"],
        "m101_b_live": inherited["m101_b_live"],
        "m102_k_live": inherited["m102_k_live"],
        "m102_c_live": inherited["m102_c_live"],
    }
    report["all_conserved"] = all(
        value is True for key, value in report.items() if key.endswith("_live")
    )
    report["report_digest"] = digest(report)
    return report


def execute_m104_world(state: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    """Execute an inherited M104 definition through the frozen M103 interface."""

    state = decode_state(state)
    predecessor = m103_runtime.decode_state(state["m104_ascii"].encode("ascii"))
    return m103_runtime.execute_world(predecessor, world)


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    state = decode_state(state)
    return {
        "schema": "m105-state-summary-v1",
        "state_digest": state["state_digest"],
        "m104_sha256": state["m104_sha256"],
        "feature_ids": [feature["feature_id"] for feature in state["features"]],
        "feature_truth_tables": [feature["truth_table"] for feature in state["features"]],
        "definition_ids": [definition["definition_id"] for definition in state["definitions"]],
        "definition_families": [definition["family"] for definition in state["definitions"]],
    }


def runtime_identity() -> dict[str, Any]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite_module": str(Path(sqlite3.__file__).resolve()),
        "json_document_interface": "python-standard-library-mapping",
    }
