"""Execution-only M102 consumer capsule.

This module decodes already adopted M102 lineage state, executes its live registry
policy for every lookup, and interprets registered definitions against record or
SQLite carriers.  It deliberately contains no candidate alphabet, enumeration,
acquisition transition, registration operation, qualification pool, expected fixture,
result writer, or verdict helper.

The sibling ``m101_executor.py`` is itself execution-only and is used to validate and
reuse the exact embedded predecessor.  Both files are copied into an isolated capsule
for fresh-process execution.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:  # Package import for tests; sibling import inside an isolated copied capsule.
    from . import m101_executor
except ImportError:  # pragma: no cover - exercised by isolated capsule tests
    import m101_executor  # type: ignore[no-redef]


STATE_SCHEMA = "m102-lineage-state-v1"
POLICY_SCHEMA = "m102-registry-policy-v1"
EVENT_SCHEMA = "m102-registry-event-v1"
C_SCHEMA = "m102-cumulative-definition-v1"
RUNTIME_SCHEMA = "m102-fresh-executor-v1"

FLAT_ORIGIN = "m102-inherited-flat"
ACQUIRED_POLICY_ORIGIN = "m102-acquired-policy"
C_ORIGIN = "m102-c"

FORBIDDEN_POLICY_SUBSTRINGS = (
    "namespace",
    "namespaced",
    "compound",
    "pair-key",
    "carrier-slot",
    "sqlite",
    "record",
    "solution",
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} is not a safe SQLite identifier")
    return value


def _policy_id(origin: str, body: list[str]) -> str:
    payload = {"schema": POLICY_SCHEMA, "origin": origin, "body": body}
    prefix = "registry-flat" if origin == FLAT_ORIGIN else "registry-policy"
    return f"{prefix}-{digest(payload)[:16]}"


def _policy_output(body: list[str], carrier: str, slot: str) -> Any | None:
    stack: list[Any] = []
    returned = False
    result: Any = None
    for token in body:
        if returned:
            return None
        if token == "LOAD_CARRIER":
            stack.append(carrier)
        elif token == "LOAD_SLOT":
            stack.append(slot)
        elif token == "PAIR":
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            stack.append([left, right])
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


def _decode_policy(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {"schema", "policy_id", "origin", "body"},
        "M102 registry policy",
    )
    if item["schema"] != POLICY_SCHEMA:
        raise ValueError("M102 policy schema mismatch")
    if item["origin"] not in {FLAT_ORIGIN, ACQUIRED_POLICY_ORIGIN}:
        raise ValueError("M102 policy origin is invalid")
    if not isinstance(item["body"], list) or not all(
        isinstance(token, str) for token in item["body"]
    ):
        raise ValueError("M102 policy body is invalid")
    if not 1 <= len(item["body"]) <= 4:
        raise ValueError("M102 policy body length is invalid")
    if item["policy_id"] != _policy_id(str(item["origin"]), list(item["body"])):
        raise ValueError("M102 policy content address mismatch")
    if item["origin"] == FLAT_ORIGIN and item["body"] != ["LOAD_SLOT", "RETURN"]:
        raise ValueError("M102 inherited flat policy changed")
    if item["origin"] == ACQUIRED_POLICY_ORIGIN:
        text = canonical_json(item).lower()
        if any(term in text for term in FORBIDDEN_POLICY_SUBSTRINGS):
            raise ValueError("M102 acquired policy contains a forbidden target identifier")
    if _policy_output(list(item["body"]), "carrier_probe", "slot_probe") is None:
        raise ValueError("M102 policy is not executable")
    return item


def _event_id(carrier: str, slot: str, descriptor: dict[str, Any]) -> str:
    payload = {
        "schema": EVENT_SCHEMA,
        "carrier": carrier,
        "slot": slot,
        "descriptor": descriptor,
    }
    return f"registry-event-{digest(payload)[:16]}"


def _decode_event(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {"schema", "event_id", "carrier", "slot", "descriptor"},
        "M102 registry event",
    )
    if item["schema"] != EVENT_SCHEMA:
        raise ValueError("M102 registry event schema mismatch")
    if not isinstance(item["carrier"], str) or not item["carrier"]:
        raise ValueError("M102 registry carrier is invalid")
    if not isinstance(item["slot"], str) or not item["slot"]:
        raise ValueError("M102 registry slot is invalid")
    if not isinstance(item["descriptor"], dict) or not isinstance(
        item["descriptor"].get("kind"), str
    ):
        raise ValueError("M102 registry descriptor is invalid")
    expected = _event_id(str(item["carrier"]), str(item["slot"]), item["descriptor"])
    if item["event_id"] != expected:
        raise ValueError("M102 registry event content address mismatch")
    return item


def _m101_ids(state: dict[str, Any]) -> tuple[str, str]:
    definitions = state["definitions"]
    if len(definitions) != 2:
        raise ValueError("M102 requires exact two-definition M101 predecessor shape")
    return str(definitions[0]["definition_id"]), str(definitions[1]["definition_id"])


def _parse_call(token: str) -> tuple[str, tuple[int, ...]] | None:
    if not token.startswith("CALL:"):
        return None
    parts = token.split(":")
    if len(parts) < 4:
        return None
    try:
        return parts[1], tuple(int(value) for value in parts[2:])
    except ValueError:
        return None


def _c_trace(body: list[str], predecessor: dict[str, Any]) -> tuple[int, ...] | None:
    a_id, b_id = _m101_ids(predecessor)
    if len(body) not in {3, 4} or body[0] != "LOAD_INPUT" or body[-1] != "RETURN":
        return None
    calls = 0
    directs = 0
    order: list[int] = []
    for token in body[1:-1]:
        call = _parse_call(token)
        if call is not None:
            calls += 1
            dependency, indices = call
            expected = 2 if dependency == a_id else 3 if dependency == b_id else 0
            if expected == 0 or len(indices) != expected:
                return None
            order.extend(indices)
        elif token.startswith("APPLY_SLOT:"):
            try:
                order.append(int(token.split(":", 1)[1]))
            except ValueError:
                return None
            directs += 1
        else:
            return None
    if calls != 1 or directs != 1:
        return None
    return tuple(order)


def _c_id(body: list[str], dependencies: list[str], policy_dependency: str) -> str:
    payload = {
        "schema": C_SCHEMA,
        "origin": C_ORIGIN,
        "body": body,
        "definition_dependencies": dependencies,
        "policy_dependency": policy_dependency,
    }
    return f"sqlite-successor-{digest(payload)[:16]}"


def _decode_c(raw: Any, predecessor: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {
            "schema",
            "definition_id",
            "origin",
            "body",
            "definition_dependencies",
            "policy_dependency",
        },
        "M102 C definition",
    )
    if item["schema"] != C_SCHEMA or item["origin"] != C_ORIGIN:
        raise ValueError("M102 C schema/origin mismatch")
    if not isinstance(item["body"], list) or not all(
        isinstance(token, str) for token in item["body"]
    ):
        raise ValueError("M102 C body is invalid")
    _a_id, b_id = _m101_ids(predecessor)
    if item["definition_dependencies"] != [b_id]:
        raise ValueError("M102 C does not retain exactly live M101 B")
    if item["policy_dependency"] != policy["policy_id"]:
        raise ValueError("M102 C does not retain the live registry policy")
    if not any(token.startswith(f"CALL:{b_id}:") for token in item["body"]):
        raise ValueError("M102 C body does not execute its declared live M101 B dependency")
    trace = _c_trace(list(item["body"]), predecessor)
    if trace is None or len(trace) != 4 or any(index not in range(4) for index in trace):
        raise ValueError("M102 C is not a well-formed four-effect definition")
    expected = _c_id(
        list(item["body"]),
        list(item["definition_dependencies"]),
        str(item["policy_dependency"]),
    )
    if item["definition_id"] != expected:
        raise ValueError("M102 C content address mismatch")
    return item


def decode_state(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"M102 state is not canonical ASCII JSON: {error}") from error
    if canonical_json(value).encode("ascii") != raw:
        raise ValueError("M102 state bytes are not canonical JSON")
    value = _closed(
        value,
        {
            "schema",
            "m101_sha256",
            "m101_ascii",
            "policy",
            "journal",
            "c_definition",
            "state_digest",
        },
        "M102 state",
    )
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    if value["state_digest"] != digest(payload):
        raise ValueError("M102 state digest mismatch")
    if value["schema"] != STATE_SCHEMA:
        raise ValueError("M102 state schema mismatch")
    if not isinstance(value["m101_ascii"], str) or not isinstance(value["m101_sha256"], str):
        raise ValueError("M102 predecessor binding is invalid")
    predecessor_raw = value["m101_ascii"].encode("ascii")
    if sha256_bytes(predecessor_raw) != value["m101_sha256"]:
        raise ValueError("M101 predecessor bytes changed")
    predecessor = m101_executor.decode_state(predecessor_raw)
    _m101_ids(predecessor)
    value["policy"] = _decode_policy(value["policy"])
    if not isinstance(value["journal"], list):
        raise ValueError("M102 registry journal is invalid")
    value["journal"] = [_decode_event(item) for item in value["journal"]]
    event_ids = [item["event_id"] for item in value["journal"]]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("M102 registry journal contains a duplicate event")
    if value["c_definition"] is not None:
        value["c_definition"] = _decode_c(
            value["c_definition"], predecessor, value["policy"]
        )
    return value


def _event_key(policy: dict[str, Any], carrier: str, slot: str) -> str:
    result = _policy_output(list(policy["body"]), carrier, slot)
    if result is None:
        raise ValueError("registry policy failed to produce a key")
    return canonical_json(result)


def _registry_index(
    state: dict[str, Any], *, last_write: bool = False
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for event in state["journal"]:
        key = _event_key(state["policy"], event["carrier"], event["slot"])
        descriptor = copy.deepcopy(event["descriptor"])
        if not last_write and key in out and out[key] != descriptor:
            raise ValueError("registry policy maps unequal descriptors to one key")
        out[key] = descriptor
    return out


def _resolve(
    state: dict[str, Any], carrier: str, slot: str, *, last_write: bool = False
) -> dict[str, Any]:
    index = _registry_index(state, last_write=last_write)
    key = _event_key(state["policy"], carrier, slot)
    if key not in index:
        raise KeyError(f"unregistered carrier/slot: {carrier}/{slot}")
    return copy.deepcopy(index[key])


def _cases(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} cases are missing")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        item = _closed(copy.deepcopy(raw), {"case_id", "input", "expected"}, f"{label} case")
        if not isinstance(item["case_id"], str) or not item["case_id"] or item["case_id"] in seen:
            raise ValueError(f"{label} case ids are invalid")
        seen.add(item["case_id"])
        out.append(item)
    return out


def _record_world(raw: Any) -> dict[str, Any]:
    world = _closed(
        copy.deepcopy(raw),
        {"schema", "world_id", "carrier", "slots", "cases"},
        "M102 record world",
    )
    if world["schema"] != "m102-record-execution-world-v1":
        raise ValueError("M102 record world schema mismatch")
    if not isinstance(world["world_id"], str) or not world["world_id"]:
        raise ValueError("M102 record world id is invalid")
    if not isinstance(world["carrier"], str) or not world["carrier"]:
        raise ValueError("M102 record carrier is invalid")
    if not isinstance(world["slots"], list) or not world["slots"] or not all(
        isinstance(slot, str) and slot for slot in world["slots"]
    ):
        raise ValueError("M102 record slots are invalid")
    world["cases"] = _cases(world["cases"], "M102 record world")
    return world


def execute_record(
    state: dict[str, Any], world: dict[str, Any], *, last_write: bool
) -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    for case in world["cases"]:
        try:
            current = copy.deepcopy(case["input"])
            for slot in world["slots"]:
                descriptor = _resolve(
                    state, world["carrier"], slot, last_write=last_write
                )
                atomic = m101_executor.atomic_from_descriptor("record", descriptor)
                current = atomic.apply(current)
            passed = current == case["expected"]
            output: Any = current
        except Exception as error:
            passed = False
            output = {"error": f"{type(error).__name__}: {error}"}
        outcomes.append({"case_id": case["case_id"], "passed": passed, "output": output})
    return {
        "schema": "m102-record-execution-v1",
        "confirmed": all(item["passed"] for item in outcomes),
        "last_write_control": last_write,
        "passed": sum(bool(item["passed"]) for item in outcomes),
        "total": len(outcomes),
        "outcomes": outcomes,
    }


def _sqlite_model(value: Any) -> dict[str, Any]:
    model = _closed(copy.deepcopy(value), {"table", "columns", "rows", "indexes"}, "SQLite model")
    _identifier(model["table"], "SQLite table")
    if not isinstance(model["columns"], list) or not model["columns"]:
        raise ValueError("SQLite model columns are invalid")
    names: list[str] = []
    for raw in model["columns"]:
        column = _closed(raw, {"name", "type"}, "SQLite model column")
        names.append(_identifier(column["name"], "SQLite column"))
        if column["type"] not in {"INTEGER", "TEXT"}:
            raise ValueError("SQLite model column type is invalid")
    if len(names) != len(set(names)):
        raise ValueError("SQLite model has duplicate columns")
    if not isinstance(model["rows"], list):
        raise ValueError("SQLite model rows are invalid")
    for row in model["rows"]:
        if not isinstance(row, dict) or set(row) != set(names):
            raise ValueError("SQLite model row is not closed over columns")
    if not isinstance(model["indexes"], list):
        raise ValueError("SQLite model indexes are invalid")
    for raw in model["indexes"]:
        index = _closed(raw, {"name", "columns"}, "SQLite model index")
        _identifier(index["name"], "SQLite index")
        if not isinstance(index["columns"], list) or not index["columns"]:
            raise ValueError("SQLite index columns are invalid")
        if any(column not in names for column in index["columns"]):
            raise ValueError("SQLite index references a missing column")
    model["indexes"].sort(key=lambda item: item["name"])
    return model


def _sql_literal(value: Any) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise ValueError("unsupported SQLite literal")


def _quote(identifier: Any) -> str:
    return '"' + _identifier(identifier, "SQL identifier") + '"'


def _apply_sql_descriptor(connection: sqlite3.Connection, descriptor: dict[str, Any]) -> None:
    kind = descriptor.get("kind")
    if kind == "add_column":
        column_type = descriptor.get("type")
        if column_type not in {"INTEGER", "TEXT"}:
            raise ValueError("invalid SQL add-column type")
        connection.execute(
            f"ALTER TABLE {_quote(descriptor.get('table'))} "
            f"ADD COLUMN {_quote(descriptor.get('column'))} {column_type} "
            f"DEFAULT {_sql_literal(descriptor.get('default'))}"
        )
    elif kind == "backfill_length":
        connection.execute(
            f"UPDATE {_quote(descriptor.get('table'))} "
            f"SET {_quote(descriptor.get('target'))} = "
            f"length({_quote(descriptor.get('source'))})"
        )
    elif kind == "rename_column":
        connection.execute(
            f"ALTER TABLE {_quote(descriptor.get('table'))} "
            f"RENAME COLUMN {_quote(descriptor.get('old'))} "
            f"TO {_quote(descriptor.get('new'))}"
        )
    elif kind == "create_index":
        columns = descriptor.get("columns")
        if not isinstance(columns, list) or not columns:
            raise ValueError("invalid SQL index columns")
        connection.execute(
            f"CREATE INDEX {_quote(descriptor.get('name'))} "
            f"ON {_quote(descriptor.get('table'))} "
            f"({','.join(_quote(item) for item in columns)})"
        )
    else:
        raise ValueError("unknown SQL descriptor")
    connection.commit()


def _materialize_sqlite(model: dict[str, Any]) -> sqlite3.Connection:
    checked = _sqlite_model(model)
    connection = sqlite3.connect(":memory:")
    columns = ",".join(
        f"{_quote(item['name'])} {item['type']}" for item in checked["columns"]
    )
    connection.execute(f"CREATE TABLE {_quote(checked['table'])} ({columns})")
    names = [item["name"] for item in checked["columns"]]
    placeholders = ",".join("?" for _ in names)
    for row in checked["rows"]:
        connection.execute(
            f"INSERT INTO {_quote(checked['table'])} "
            f"({','.join(_quote(name) for name in names)}) VALUES ({placeholders})",
            tuple(row[name] for name in names),
        )
    for index in checked["indexes"]:
        connection.execute(
            f"CREATE INDEX {_quote(index['name'])} ON {_quote(checked['table'])} "
            f"({','.join(_quote(item) for item in index['columns'])})"
        )
    connection.commit()
    return connection


def _snapshot_sqlite(connection: sqlite3.Connection, table: str) -> dict[str, Any]:
    table = _identifier(table, "snapshot table")
    columns = [
        {"name": row[1], "type": str(row[2]).upper()}
        for row in connection.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
    ]
    names = [item["name"] for item in columns]
    rows = [
        dict(zip(names, row, strict=True))
        for row in connection.execute(
            f"SELECT {','.join(_quote(name) for name in names)} "
            f"FROM {_quote(table)} ORDER BY {_quote(names[0])}"
        ).fetchall()
    ]
    indexes: list[dict[str, Any]] = []
    for row in connection.execute(f"PRAGMA index_list({_quote(table)})").fetchall():
        name = str(row[1])
        if name.startswith("sqlite_autoindex"):
            continue
        index_columns = [
            str(info[2])
            for info in connection.execute(f"PRAGMA index_info({_quote(name)})").fetchall()
        ]
        indexes.append({"name": name, "columns": index_columns})
    indexes.sort(key=lambda item: item["name"])
    if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
        raise ValueError("SQLite integrity check failed")
    return _sqlite_model(
        {"table": table, "columns": columns, "rows": rows, "indexes": indexes}
    )


@dataclass(frozen=True)
class Atomic:
    descriptor: dict[str, Any]
    apply: Callable[[Any], Any]


def _initial(value: Any) -> Any:
    return value if isinstance(value, sqlite3.Connection) else copy.deepcopy(value)


def _execute_a(a: dict[str, Any], value: Any, slots: tuple[Atomic, Atomic]) -> Any | None:
    stack: list[Any] = []
    returned = False
    result: Any = None
    for token in a["body"]:
        if returned:
            return None
        if token == "LOAD_INPUT":
            stack.append(_initial(value))
        elif token == "APPLY_SLOT:0":
            if not stack:
                return None
            stack.append(slots[0].apply(stack.pop()))
        elif token == "APPLY_SLOT:1":
            if not stack:
                return None
            stack.append(slots[1].apply(stack.pop()))
        elif token == "DUP":
            if not stack or isinstance(stack[-1], sqlite3.Connection):
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


def _execute_b(
    predecessor: dict[str, Any], value: Any, slots: tuple[Atomic, Atomic, Atomic]
) -> Any | None:
    a, b = predecessor["definitions"]
    current: Any = None
    loaded = False
    returned = False
    for token in b["body"]:
        if returned:
            return None
        if token == "LOAD_INPUT":
            if loaded:
                return None
            current = _initial(value)
            loaded = True
        elif token.startswith("CALL:"):
            call = _parse_call(token)
            if not loaded or call is None:
                return None
            dependency, indices = call
            if dependency != a["definition_id"] or len(indices) != 2:
                return None
            current = _execute_a(a, current, (slots[indices[0]], slots[indices[1]]))
            if current is None:
                return None
        elif token.startswith("APPLY_SLOT:"):
            if not loaded:
                return None
            try:
                index = int(token.split(":", 1)[1])
            except ValueError:
                return None
            if index not in range(3):
                return None
            current = slots[index].apply(current)
        elif token == "RETURN":
            if not loaded:
                return None
            returned = True
        else:
            return None
    return current if returned else None


def _execute_c(
    c_item: dict[str, Any], predecessor: dict[str, Any], connection: sqlite3.Connection,
    slots: tuple[Atomic, ...]
) -> sqlite3.Connection | None:
    if _c_trace(list(c_item["body"]), predecessor) is None:
        return None
    _a, b = predecessor["definitions"]
    current: Any = connection
    for token in c_item["body"][1:-1]:
        call = _parse_call(token)
        if call is not None:
            dependency, indices = call
            if dependency != b["definition_id"] or len(indices) != 3:
                return None
            current = _execute_b(
                predecessor,
                current,
                (slots[indices[0]], slots[indices[1]], slots[indices[2]]),
            )
        else:
            try:
                index = int(token.split(":", 1)[1])
            except (IndexError, ValueError):
                return None
            if index not in range(len(slots)):
                return None
            current = slots[index].apply(current)
        if current is None:
            return None
    return current if isinstance(current, sqlite3.Connection) else None


def _sqlite_world(raw: Any) -> dict[str, Any]:
    world = _closed(
        copy.deepcopy(raw),
        {"schema", "world_id", "slots", "cases"},
        "M102 SQLite world",
    )
    if world["schema"] != "m102-sqlite-execution-world-v1":
        raise ValueError("M102 SQLite world schema mismatch")
    if not isinstance(world["world_id"], str) or not world["world_id"]:
        raise ValueError("M102 SQLite world id is invalid")
    if not isinstance(world["slots"], list) or len(world["slots"]) != 4 or not all(
        isinstance(slot, str) and slot for slot in world["slots"]
    ):
        raise ValueError("M102 SQLite slots are invalid")
    if len(set(world["slots"])) != 4:
        raise ValueError("M102 SQLite slots must be distinct")
    world["cases"] = _cases(world["cases"], "M102 SQLite world")
    for case in world["cases"]:
        case["input"] = _sqlite_model(case["input"])
        case["expected"] = _sqlite_model(case["expected"])
    return world


def execute_sqlite(state: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    c_item = state["c_definition"]
    if c_item is None:
        return {
            "schema": "m102-sqlite-execution-v1",
            "confirmed": False,
            "reason": "C is absent",
            "passed": 0,
            "total": len(world["cases"]),
            "outcomes": [],
        }
    predecessor = m101_executor.decode_state(state["m101_ascii"].encode("ascii"))
    descriptors = [_resolve(state, "sqlite", slot) for slot in world["slots"]]
    atomics = tuple(
        Atomic(
            copy.deepcopy(descriptor),
            lambda connection, item=copy.deepcopy(descriptor): (
                _apply_sql_descriptor(connection, item) or connection
            ),
        )
        for descriptor in descriptors
    )
    outcomes: list[dict[str, Any]] = []
    for case in world["cases"]:
        connection: sqlite3.Connection | None = None
        try:
            connection = _materialize_sqlite(case["input"])
            result = _execute_c(c_item, predecessor, connection, atomics)
            if result is not connection:
                raise ValueError("C did not return the live SQLite connection")
            snapshot = _snapshot_sqlite(connection, case["input"]["table"])
            passed = snapshot == case["expected"]
            outcome = {
                "case_id": case["case_id"],
                "passed": passed,
                "snapshot": snapshot,
                "expected": copy.deepcopy(case["expected"]),
            }
        except Exception as error:
            outcome = {
                "case_id": case["case_id"],
                "passed": False,
                "snapshot": None,
                "expected": copy.deepcopy(case["expected"]),
                "error": f"{type(error).__name__}: {error}",
            }
        finally:
            if connection is not None:
                connection.close()
        outcomes.append(outcome)
    return {
        "schema": "m102-sqlite-execution-v1",
        "confirmed": all(item["passed"] for item in outcomes),
        "passed": sum(bool(item["passed"]) for item in outcomes),
        "total": len(outcomes),
        "outcomes": outcomes,
    }


def _project_modules() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if name.startswith(("metamorphosis", "scripts", "mira_core", "m102_runtime"))
    )


def _load_world(path: Path) -> tuple[bytes, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"world is not canonical ASCII JSON: {error}") from error
    if canonical_json(value).encode("ascii") != raw:
        raise ValueError("world bytes are not canonical JSON")
    return raw, value


def run(action: str, state_path: Path, world_path: Path, *, last_write: bool) -> dict[str, Any]:
    state_raw = state_path.read_bytes()
    state = decode_state(state_raw)
    world_raw, world_value = _load_world(world_path)
    predecessor = m101_executor.decode_state(state["m101_ascii"].encode("ascii"))
    if action == "execute-record":
        execution = execute_record(state, _record_world(world_value), last_write=last_write)
    elif action == "execute-sqlite":
        if last_write:
            raise ValueError("last-write mode is only valid for record control execution")
        execution = execute_sqlite(state, _sqlite_world(world_value))
    elif action == "execute-m101-a":
        execution = m101_executor.execute_a(predecessor, m101_executor._world(world_value))
    elif action == "execute-m101-b":
        execution = m101_executor.execute_b(predecessor, m101_executor._world(world_value))
    elif action == "execute-m100":
        execution = m101_executor.execute_m100(
            predecessor, m101_executor._m100_world(world_value)
        )
    else:
        raise ValueError("unknown M102 execution action")
    return {
        "schema": RUNTIME_SCHEMA,
        "action": action,
        "pid": os.getpid(),
        "isolated_mode": sys.flags.isolated == 1,
        "state_raw_sha256": sha256_bytes(state_raw),
        "world_raw_sha256": sha256_bytes(world_raw),
        "state_digest": state["state_digest"],
        "m101_sha256": state["m101_sha256"],
        "policy_id": state["policy"]["policy_id"],
        "event_count": len(state["journal"]),
        "c_definition_id": (
            state["c_definition"]["definition_id"]
            if state["c_definition"] is not None
            else None
        ),
        "confirmed": execution["confirmed"],
        "execution": execution,
        "sqlite_version": sqlite3.sqlite_version,
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
        "imported_project_modules": _project_modules(),
        "search_path": [str(item) for item in sys.path],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "execute-record",
            "execute-sqlite",
            "execute-m101-a",
            "execute-m101-b",
            "execute-m100",
        ),
    )
    parser.add_argument("--state", required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument("--last-write", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run(
            arguments.action,
            Path(arguments.state),
            Path(arguments.world),
            last_write=bool(arguments.last_write),
        )
    except Exception as error:
        result = {
            "schema": RUNTIME_SCHEMA,
            "action": arguments.action,
            "pid": os.getpid(),
            "isolated_mode": sys.flags.isolated == 1,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
            "sqlite_version": sqlite3.sqlite_version,
            "model_calls": 0,
            "network_calls": 0,
            "remote_execution_calls": 0,
            "imported_project_modules": _project_modules(),
            "search_path": [str(item) for item in sys.path],
        }
        print(json.dumps(result, sort_keys=True))
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0 if result["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
