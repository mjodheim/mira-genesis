"""Bounded M102 registry-policy acquisition and cumulative SQLite runtime.

M102 embeds the exact positive M101 T2 bytes, makes registry addressing executable
state, and allows one generic addressing-policy definition to be acquired after an
observable flat-key collision.  A later four-effect definition must use live M101 B
and the acquired policy.  SQLite execution is local and scored from database state.

This is an authored bounded substrate.  It has no network, repository, credential,
deployment, evaluator-changing or permission-changing authority.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable, Iterable

try:  # The same file must work both as a package module and in a copied capsule.
    from . import m101_runtime
except ImportError:  # pragma: no cover - exercised by isolated capsule tests
    import m101_runtime  # type: ignore[no-redef]


STATE_SCHEMA = "m102-lineage-state-v1"
POLICY_SCHEMA = "m102-registry-policy-v1"
EVENT_SCHEMA = "m102-registry-event-v1"
C_SCHEMA = "m102-cumulative-definition-v1"
POLICY_DEMAND_SCHEMA = "m102-policy-demand-v1"
C_DEMAND_SCHEMA = "m102-c-demand-v1"

FLAT_ORIGIN = "m102-inherited-flat"
ACQUIRED_POLICY_ORIGIN = "m102-acquired-policy"
C_ORIGIN = "m102-c"

POLICY_TOKENS = (
    "LOAD_CARRIER",
    "LOAD_SLOT",
    "PAIR",
    "DUP",
    "SWAP",
    "RETURN",
)
POLICY_MAX_BODY = 4
C_MAX_TRANSFORMS = 2

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


def policy_definition(origin: str, body: Iterable[str]) -> dict[str, Any]:
    body_list = list(body)
    return {
        "schema": POLICY_SCHEMA,
        "policy_id": _policy_id(origin, body_list),
        "origin": origin,
        "body": body_list,
    }


def inherited_flat_policy() -> dict[str, Any]:
    return policy_definition(FLAT_ORIGIN, ["LOAD_SLOT", "RETURN"])


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


def decode_policy(raw: dict[str, Any]) -> dict[str, Any]:
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
        isinstance(token, str) and token in POLICY_TOKENS for token in item["body"]
    ):
        raise ValueError("M102 policy body is invalid")
    if not 1 <= len(item["body"]) <= POLICY_MAX_BODY:
        raise ValueError("M102 policy body length is invalid")
    if item["policy_id"] != _policy_id(str(item["origin"]), list(item["body"])):
        raise ValueError("M102 policy content address mismatch")
    if item["origin"] == FLAT_ORIGIN and item != inherited_flat_policy():
        raise ValueError("M102 inherited flat policy changed")
    if item["origin"] == ACQUIRED_POLICY_ORIGIN:
        text = canonical_json(item).lower()
        if any(term in text for term in FORBIDDEN_POLICY_SUBSTRINGS):
            raise ValueError("M102 acquired policy contains a forbidden target identifier")
    if _policy_output(list(item["body"]), "carrier_probe", "slot_probe") is None:
        raise ValueError("M102 policy is not executable")
    return item


def registry_event(carrier: str, slot: str, descriptor: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(carrier, str) or not carrier:
        raise ValueError("registry carrier is invalid")
    if not isinstance(slot, str) or not slot:
        raise ValueError("registry slot is invalid")
    if not isinstance(descriptor, dict) or not isinstance(descriptor.get("kind"), str):
        raise ValueError("registry descriptor is invalid")
    payload = {
        "schema": EVENT_SCHEMA,
        "carrier": carrier,
        "slot": slot,
        "descriptor": copy.deepcopy(descriptor),
    }
    return {"event_id": f"registry-event-{digest(payload)[:16]}", **payload}


def decode_event(raw: dict[str, Any]) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {"schema", "event_id", "carrier", "slot", "descriptor"},
        "M102 registry event",
    )
    expected = registry_event(str(item["carrier"]), str(item["slot"]), item["descriptor"])
    if item != expected:
        raise ValueError("M102 registry event content address mismatch")
    return item


def _m101_ids(m101_state: dict[str, Any]) -> tuple[str, str]:
    definitions = m101_state["definitions"]
    if len(definitions) != 2:
        raise ValueError("M102 requires exact M101 T2 with A and B")
    return str(definitions[0]["definition_id"]), str(definitions[1]["definition_id"])


def _c_id(
    body: list[str], definition_dependencies: list[str], policy_dependency: str
) -> str:
    payload = {
        "schema": C_SCHEMA,
        "origin": C_ORIGIN,
        "body": body,
        "definition_dependencies": definition_dependencies,
        "policy_dependency": policy_dependency,
    }
    return f"sqlite-successor-{digest(payload)[:16]}"


def c_definition(
    body: Iterable[str], *, b_id: str, policy_id: str
) -> dict[str, Any]:
    body_list = list(body)
    deps = [b_id]
    return {
        "schema": C_SCHEMA,
        "definition_id": _c_id(body_list, deps, policy_id),
        "origin": C_ORIGIN,
        "body": body_list,
        "definition_dependencies": deps,
        "policy_dependency": policy_id,
    }


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


def c_symbolic_trace(body: list[str], m101_state: dict[str, Any]) -> tuple[int, ...] | None:
    a_id, b_id = _m101_ids(m101_state)
    if len(body) not in {3, 4} or body[0] != "LOAD_INPUT" or body[-1] != "RETURN":
        return None
    transforms = body[1:-1]
    order: list[int] = []
    calls = 0
    directs = 0
    for token in transforms:
        call = _parse_call(token)
        if call is not None:
            calls += 1
            dep, indices = call
            expected = 2 if dep == a_id else 3 if dep == b_id else 0
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


def decode_c_definition(
    raw: dict[str, Any], *, m101_state: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
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
    _a_id, b_id = _m101_ids(m101_state)
    if item["definition_dependencies"] != [b_id]:
        raise ValueError("M102 C does not retain exactly live M101 B")
    if item["policy_dependency"] != policy["policy_id"]:
        raise ValueError("M102 C does not retain the live registry policy")
    if not any(token.startswith(f"CALL:{b_id}:") for token in item["body"]):
        raise ValueError("M102 C body does not execute its declared live M101 B dependency")
    trace = c_symbolic_trace(list(item["body"]), m101_state)
    if trace is None or len(trace) != 4 or any(index not in range(4) for index in trace):
        raise ValueError("M102 C is not a well-formed four-effect definition")
    if item["definition_id"] != _c_id(
        list(item["body"]), list(item["definition_dependencies"]), str(item["policy_dependency"])
    ):
        raise ValueError("M102 C content address mismatch")
    return item


def _state(
    m101_bytes: bytes,
    policy: dict[str, Any],
    journal: list[dict[str, Any]],
    c_item: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": STATE_SCHEMA,
        "m101_sha256": sha256_bytes(m101_bytes),
        "m101_ascii": m101_bytes.decode("ascii"),
        "policy": copy.deepcopy(policy),
        "journal": copy.deepcopy(journal),
        "c_definition": copy.deepcopy(c_item),
    }
    payload["state_digest"] = digest(payload)
    return payload


def create_state(m101_bytes: bytes, prior_events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    m101_state = m101_runtime.decode_state(m101_bytes)
    _m101_ids(m101_state)
    events = [decode_event(item) for item in prior_events]
    state = _state(m101_bytes, inherited_flat_policy(), events, None)
    registry_index(state)  # U0 must be valid under the inherited flat policy.
    return decode_state(state)


def decode_state(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        value = copy.deepcopy(raw)
    else:
        raw_bytes = raw.encode("ascii") if isinstance(raw, str) else raw
        try:
            value = json.loads(raw_bytes.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"M102 state is not canonical ASCII JSON: {error}") from error
        if canonical_json(value).encode("ascii") != raw_bytes:
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
    m101_bytes = value["m101_ascii"].encode("ascii")
    if sha256_bytes(m101_bytes) != value["m101_sha256"]:
        raise ValueError("M101 predecessor bytes changed")
    m101_state = m101_runtime.decode_state(m101_bytes)
    _m101_ids(m101_state)
    value["policy"] = decode_policy(value["policy"])
    if not isinstance(value["journal"], list):
        raise ValueError("M102 registry journal is invalid")
    value["journal"] = [decode_event(item) for item in value["journal"]]
    event_ids = [item["event_id"] for item in value["journal"]]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("M102 registry journal contains a duplicate event")
    if value["c_definition"] is not None:
        value["c_definition"] = decode_c_definition(
            value["c_definition"], m101_state=m101_state, policy=value["policy"]
        )
    return value


def encode_state(state: dict[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


def _event_key(policy: dict[str, Any], carrier: str, slot: str) -> str:
    output = _policy_output(list(policy["body"]), carrier, slot)
    if output is None:
        raise ValueError("registry policy failed to produce a key")
    return canonical_json(output)


def registry_index(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checked = decode_state(state)
    out: dict[str, dict[str, Any]] = {}
    for event in checked["journal"]:
        key = _event_key(checked["policy"], str(event["carrier"]), str(event["slot"]))
        descriptor = copy.deepcopy(event["descriptor"])
        if key in out and out[key] != descriptor:
            raise ValueError("registry policy maps unequal descriptors to one key")
        out[key] = descriptor
    return out


def registry_index_last_write(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checked = decode_state(state)
    out: dict[str, dict[str, Any]] = {}
    for event in checked["journal"]:
        key = _event_key(checked["policy"], str(event["carrier"]), str(event["slot"]))
        out[key] = copy.deepcopy(event["descriptor"])
    return out


def resolve_descriptor(
    state: dict[str, Any], carrier: str, slot: str, *, last_write: bool = False
) -> dict[str, Any]:
    checked = decode_state(state)
    index = registry_index_last_write(checked) if last_write else registry_index(checked)
    key = _event_key(checked["policy"], carrier, slot)
    if key not in index:
        raise KeyError(f"unregistered carrier/slot: {carrier}/{slot}")
    return copy.deepcopy(index[key])


def flat_collision_report(
    state: dict[str, Any], incoming_events: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    checked = decode_state(state)
    if checked["policy"] != inherited_flat_policy():
        raise ValueError("flat collision report requires U0")
    events = list(checked["journal"]) + [decode_event(item) for item in incoming_events]
    by_key: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        key = _event_key(checked["policy"], event["carrier"], event["slot"])
        by_key.setdefault(key, []).append(event)
    witnesses: list[dict[str, Any]] = []
    for key, members in sorted(by_key.items()):
        descriptor_digests = sorted({digest(item["descriptor"]) for item in members})
        if len(descriptor_digests) > 1:
            witnesses.append(
                {
                    "key": key,
                    "event_ids": sorted(item["event_id"] for item in members),
                    "descriptor_digests": descriptor_digests,
                }
            )
    return {
        "schema": "m102-flat-closure-v1",
        "policy_body": checked["policy"]["body"],
        "event_count": len(events),
        "distinct_output_keys": len(by_key),
        "collision_witnesses": witnesses,
        "joint_relation_representable": not witnesses,
        "budget_independent": True,
    }


def _lookups(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} lookups are missing")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        item = _closed(
            copy.deepcopy(raw),
            {"case_id", "carrier", "slot", "expected_descriptor"},
            f"{label} lookup",
        )
        if not isinstance(item["case_id"], str) or not item["case_id"] or item["case_id"] in seen:
            raise ValueError(f"{label} lookup id is invalid")
        seen.add(item["case_id"])
        if not isinstance(item["carrier"], str) or not isinstance(item["slot"], str):
            raise ValueError(f"{label} lookup key is invalid")
        if not isinstance(item["expected_descriptor"], dict):
            raise ValueError(f"{label} lookup descriptor is invalid")
        out.append(item)
    return out


def decode_policy_demand(raw: dict[str, Any]) -> dict[str, Any]:
    value = _closed(
        copy.deepcopy(raw),
        {"schema", "world_id", "role", "incoming_events", "public_lookups"},
        "M102 policy demand",
    )
    if value["schema"] != POLICY_DEMAND_SCHEMA or value["role"] != "policy_producer_trigger":
        raise ValueError("M102 policy demand schema/role mismatch")
    if not isinstance(value["world_id"], str) or not value["world_id"]:
        raise ValueError("M102 policy demand world id is invalid")
    if not isinstance(value["incoming_events"], list) or not value["incoming_events"]:
        raise ValueError("M102 policy demand events are missing")
    value["incoming_events"] = [decode_event(item) for item in value["incoming_events"]]
    value["public_lookups"] = _lookups(value["public_lookups"], "policy demand")
    return value


def policy_demand(
    world_id: str,
    incoming_events: Iterable[dict[str, Any]],
    public_lookups: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return decode_policy_demand(
        {
            "schema": POLICY_DEMAND_SCHEMA,
            "world_id": world_id,
            "role": "policy_producer_trigger",
            "incoming_events": list(incoming_events),
            "public_lookups": list(public_lookups),
        }
    )


def _lookups_pass(state: dict[str, Any], lookups: list[dict[str, Any]]) -> bool:
    try:
        return all(
            resolve_descriptor(state, item["carrier"], item["slot"])
            == item["expected_descriptor"]
            for item in lookups
        )
    except (KeyError, ValueError):
        return False


def acquire_policy(
    state: dict[str, Any], demand: dict[str, Any], *, register_result: bool
) -> dict[str, Any]:
    checked = decode_state(state)
    if checked["policy"] != inherited_flat_policy() or checked["c_definition"] is not None:
        raise ValueError("policy acquisition requires U0")
    public = decode_policy_demand(demand)
    incoming = public["incoming_events"]
    closure = flat_collision_report(checked, incoming)
    if closure["joint_relation_representable"]:
        return {
            "schema": "m102-policy-acquisition-v1",
            "confirmed": False,
            "reason": "inherited flat policy already represents the public relation",
            "assembled": 0,
            "well_formed": 0,
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "flat_closure": closure,
            "public_case_ids": [item["case_id"] for item in public["public_lookups"]],
        }

    assembled = 0
    well_formed = 0
    accepted: list[tuple[list[str], dict[str, Any]]] = []
    for length in range(1, POLICY_MAX_BODY + 1):
        for body_tuple in itertools.product(POLICY_TOKENS, repeat=length):
            assembled += 1
            body = list(body_tuple)
            if _policy_output(body, "carrier_probe", "slot_probe") is None:
                continue
            well_formed += 1
            candidate = policy_definition(ACQUIRED_POLICY_ORIGIN, body)
            descendant = _state(
                checked["m101_ascii"].encode("ascii"),
                candidate,
                list(checked["journal"]) + incoming,
                None,
            )
            try:
                registry_index(descendant)
            except ValueError:
                continue
            if _lookups_pass(descendant, public["public_lookups"]):
                accepted.append((body, candidate))
    accepted.sort(key=lambda item: (len(item[0]), digest(item[0])))
    if not accepted:
        return {
            "schema": "m102-policy-acquisition-v1",
            "confirmed": False,
            "assembled": assembled,
            "well_formed": well_formed,
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "flat_closure": closure,
            "public_case_ids": [item["case_id"] for item in public["public_lookups"]],
        }
    selected_body, adopted = accepted[0]
    next_state = (
        decode_state(
            _state(
                checked["m101_ascii"].encode("ascii"),
                adopted,
                list(checked["journal"]) + incoming,
                None,
            )
        )
        if register_result
        else None
    )
    return {
        "schema": "m102-policy-acquisition-v1",
        "confirmed": True,
        "assembled": assembled,
        "well_formed": well_formed,
        "accepted": len(accepted),
        "shortest_accepted_length": len(selected_body),
        "adopted": adopted,
        "registered": bool(register_result),
        "next_state": next_state,
        "flat_closure": closure,
        "public_case_ids": [item["case_id"] for item in public["public_lookups"]],
    }


def register_events(
    state: dict[str, Any], incoming_events: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    checked = decode_state(state)
    events = list(checked["journal"]) + [decode_event(item) for item in incoming_events]
    descendant = decode_state(
        _state(
            checked["m101_ascii"].encode("ascii"),
            checked["policy"],
            events,
            checked["c_definition"],
        )
    )
    registry_index(descendant)
    return descendant


def force_last_write_events(
    state: dict[str, Any], incoming_events: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    """Materialise the destructive no-upgrade control without hiding the collision."""
    checked = decode_state(state)
    return decode_state(
        _state(
            checked["m101_ascii"].encode("ascii"),
            checked["policy"],
            list(checked["journal"]) + [decode_event(item) for item in incoming_events],
            checked["c_definition"],
        )
    )


@dataclass(frozen=True)
class Atomic:
    descriptor: dict[str, Any]
    apply: Callable[[Any], Any]


def _record_atomic(descriptor: dict[str, Any]) -> Atomic:
    inherited = m101_runtime.atomic_from_descriptor("record", descriptor)
    return Atomic(copy.deepcopy(descriptor), inherited.apply)


def execute_registry_sequence(
    state: dict[str, Any], carrier: str, slots: Iterable[str], value: Any, *, last_write: bool = False
) -> Any:
    current = copy.deepcopy(value)
    for slot in slots:
        descriptor = resolve_descriptor(state, carrier, slot, last_write=last_write)
        current = _record_atomic(descriptor).apply(current)
    return current


def _sqlite_model(value: Any) -> dict[str, Any]:
    model = _closed(
        copy.deepcopy(value),
        {"table", "columns", "rows", "indexes"},
        "SQLite model",
    )
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


def _sqlite_model_atomic(descriptor: dict[str, Any]) -> Atomic:
    kind = descriptor.get("kind")
    if kind == "add_column":
        table = _identifier(descriptor.get("table"), "add_column table")
        column = _identifier(descriptor.get("column"), "add_column column")
        column_type = descriptor.get("type")
        default = descriptor.get("default")
        if column_type not in {"INTEGER", "TEXT"} or not isinstance(default, (int, str)):
            raise ValueError("add_column descriptor is invalid")

        def apply(value: Any) -> Any:
            model = _sqlite_model(value)
            if model["table"] != table or any(item["name"] == column for item in model["columns"]):
                raise ValueError("add_column precondition failed")
            model["columns"].append({"name": column, "type": column_type})
            for row in model["rows"]:
                row[column] = copy.deepcopy(default)
            return model

        return Atomic(copy.deepcopy(descriptor), apply)

    if kind == "backfill_length":
        table = _identifier(descriptor.get("table"), "backfill table")
        source = _identifier(descriptor.get("source"), "backfill source")
        target = _identifier(descriptor.get("target"), "backfill target")

        def apply(value: Any) -> Any:
            model = _sqlite_model(value)
            names = [item["name"] for item in model["columns"]]
            if model["table"] != table or source not in names or target not in names:
                raise ValueError("backfill precondition failed")
            for row in model["rows"]:
                if not isinstance(row[source], str):
                    raise ValueError("backfill source is not text")
                row[target] = len(row[source])
            return model

        return Atomic(copy.deepcopy(descriptor), apply)

    if kind == "rename_column":
        table = _identifier(descriptor.get("table"), "rename table")
        old = _identifier(descriptor.get("old"), "rename old")
        new = _identifier(descriptor.get("new"), "rename new")

        def apply(value: Any) -> Any:
            model = _sqlite_model(value)
            names = [item["name"] for item in model["columns"]]
            if model["table"] != table or old not in names or new in names:
                raise ValueError("rename precondition failed")
            for column in model["columns"]:
                if column["name"] == old:
                    column["name"] = new
            for row in model["rows"]:
                row[new] = row.pop(old)
            for index in model["indexes"]:
                index["columns"] = [new if item == old else item for item in index["columns"]]
            return model

        return Atomic(copy.deepcopy(descriptor), apply)

    if kind == "create_index":
        table = _identifier(descriptor.get("table"), "index table")
        name = _identifier(descriptor.get("name"), "index name")
        columns = descriptor.get("columns")
        if not isinstance(columns, list) or not columns:
            raise ValueError("create_index columns are invalid")
        columns = [_identifier(item, "index column") for item in columns]

        def apply(value: Any) -> Any:
            model = _sqlite_model(value)
            names = [item["name"] for item in model["columns"]]
            if model["table"] != table or any(item not in names for item in columns):
                raise ValueError("create_index precondition failed")
            if any(item["name"] == name for item in model["indexes"]):
                raise ValueError("index already exists")
            model["indexes"].append({"name": name, "columns": list(columns)})
            model["indexes"].sort(key=lambda item: item["name"])
            return model

        return Atomic(copy.deepcopy(descriptor), apply)
    raise ValueError("unknown SQLite descriptor")


def _initial_value(value: Any) -> Any:
    return value if isinstance(value, sqlite3.Connection) else copy.deepcopy(value)


def _execute_a(
    a: dict[str, Any], value: Any, slots: tuple[Atomic, Atomic]
) -> Any | None:
    stack: list[Any] = []
    result: Any = None
    returned = False
    for token in a["body"]:
        if returned:
            return None
        if token == "LOAD_INPUT":
            stack.append(_initial_value(value))
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
    m101_state: dict[str, Any], value: Any, slots: tuple[Atomic, Atomic, Atomic]
) -> Any | None:
    a, b = m101_state["definitions"]
    current: Any = None
    loaded = False
    returned = False
    for token in b["body"]:
        if returned:
            return None
        if token == "LOAD_INPUT":
            if loaded:
                return None
            current = _initial_value(value)
            loaded = True
        elif token.startswith("CALL:"):
            call = _parse_call(token)
            if not loaded or call is None:
                return None
            dep, indices = call
            if dep != a["definition_id"] or len(indices) != 2:
                return None
            current = _execute_a(a, current, (slots[indices[0]], slots[indices[1]]))
            if current is None:
                return None
        elif token.startswith("APPLY_SLOT:"):
            if not loaded:
                return None
            index = int(token.split(":", 1)[1])
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


def execute_c_body(
    body: list[str], m101_state: dict[str, Any], value: Any, slots: tuple[Atomic, ...]
) -> Any | None:
    if c_symbolic_trace(body, m101_state) is None:
        return None
    a, b = m101_state["definitions"]
    current = _initial_value(value)
    for token in body[1:-1]:
        call = _parse_call(token)
        if call is not None:
            dep, indices = call
            if dep == a["definition_id"] and len(indices) == 2:
                current = _execute_a(a, current, (slots[indices[0]], slots[indices[1]]))
            elif dep == b["definition_id"] and len(indices) == 3:
                current = _execute_b(
                    m101_state,
                    current,
                    (slots[indices[0]], slots[indices[1]], slots[indices[2]]),
                )
            else:
                return None
            if current is None:
                return None
        else:
            index = int(token.split(":", 1)[1])
            current = slots[index].apply(current)
    return current


def _c_cases(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} cases are missing")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        item = _closed(copy.deepcopy(raw), {"case_id", "input", "expected"}, f"{label} case")
        if not isinstance(item["case_id"], str) or not item["case_id"] or item["case_id"] in seen:
            raise ValueError(f"{label} case id is invalid")
        seen.add(item["case_id"])
        item["input"] = _sqlite_model(item["input"])
        item["expected"] = _sqlite_model(item["expected"])
        out.append(item)
    return out


def decode_c_demand(raw: dict[str, Any]) -> dict[str, Any]:
    value = _closed(
        copy.deepcopy(raw),
        {"schema", "world_id", "role", "carrier", "slots", "public_cases"},
        "M102 C demand",
    )
    if value["schema"] != C_DEMAND_SCHEMA or value["role"] != "sqlite_c_trigger":
        raise ValueError("M102 C demand schema/role mismatch")
    if value["carrier"] != "sqlite" or not isinstance(value["world_id"], str):
        raise ValueError("M102 C demand carrier/world is invalid")
    if not isinstance(value["slots"], list) or len(value["slots"]) != 4 or not all(
        isinstance(slot, str) and slot for slot in value["slots"]
    ):
        raise ValueError("M102 C demand slots are invalid")
    if len(set(value["slots"])) != 4:
        raise ValueError("M102 C demand slots must be distinct")
    value["public_cases"] = _c_cases(value["public_cases"], "C demand")
    return value


def c_demand(world_id: str, slots: list[str], public_cases: list[dict[str, Any]]) -> dict[str, Any]:
    return decode_c_demand(
        {
            "schema": C_DEMAND_SCHEMA,
            "world_id": world_id,
            "role": "sqlite_c_trigger",
            "carrier": "sqlite",
            "slots": slots,
            "public_cases": public_cases,
        }
    )


def _resolved_sqlite_atomics(state: dict[str, Any], slots: list[str]) -> tuple[Atomic, ...]:
    return tuple(
        _sqlite_model_atomic(resolve_descriptor(state, "sqlite", slot)) for slot in slots
    )


def _sql_literal(value: Any) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise ValueError("unsupported SQLite literal")


def _quote(identifier: str) -> str:
    return '"' + _identifier(identifier, "SQL identifier") + '"'


def _apply_sql_descriptor(connection: sqlite3.Connection, descriptor: dict[str, Any]) -> sqlite3.Connection:
    kind = descriptor.get("kind")
    if kind == "add_column":
        table = _quote(descriptor["table"])
        column = _quote(descriptor["column"])
        column_type = descriptor["type"]
        if column_type not in {"INTEGER", "TEXT"}:
            raise ValueError("invalid SQL add-column type")
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {column_type} DEFAULT {_sql_literal(descriptor['default'])}"
        )
    elif kind == "backfill_length":
        connection.execute(
            f"UPDATE {_quote(descriptor['table'])} SET {_quote(descriptor['target'])} = length({_quote(descriptor['source'])})"
        )
    elif kind == "rename_column":
        connection.execute(
            f"ALTER TABLE {_quote(descriptor['table'])} RENAME COLUMN {_quote(descriptor['old'])} TO {_quote(descriptor['new'])}"
        )
    elif kind == "create_index":
        columns = ",".join(_quote(item) for item in descriptor["columns"])
        connection.execute(
            f"CREATE INDEX {_quote(descriptor['name'])} ON {_quote(descriptor['table'])} ({columns})"
        )
    else:
        raise ValueError("unknown SQL descriptor")
    connection.commit()
    return connection


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
            f"INSERT INTO {_quote(checked['table'])} ({','.join(_quote(name) for name in names)}) VALUES ({placeholders})",
            tuple(row[name] for name in names),
        )
    for index in checked["indexes"]:
        cols = ",".join(_quote(item) for item in index["columns"])
        connection.execute(
            f"CREATE INDEX {_quote(index['name'])} ON {_quote(checked['table'])} ({cols})"
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
            f"SELECT {','.join(_quote(name) for name in names)} FROM {_quote(table)} ORDER BY {_quote(names[0])}"
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
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity != ("ok",):
        raise ValueError("SQLite integrity check failed")
    return _sqlite_model({"table": table, "columns": columns, "rows": rows, "indexes": indexes})


def execute_sqlite_case(
    state: dict[str, Any], c_item: dict[str, Any], case: dict[str, Any], slots: list[str]
) -> dict[str, Any]:
    checked = decode_state(state)
    m101_state = m101_runtime.decode_state(checked["m101_ascii"].encode("ascii"))
    descriptors = [resolve_descriptor(checked, "sqlite", slot) for slot in slots]
    atomics = tuple(
        Atomic(copy.deepcopy(descriptor), lambda connection, d=copy.deepcopy(descriptor): _apply_sql_descriptor(connection, d))
        for descriptor in descriptors
    )
    connection = _materialize_sqlite(case["input"])
    try:
        result = execute_c_body(list(c_item["body"]), m101_state, connection, atomics)
        if result is not connection:
            raise ValueError("C did not return the live SQLite connection")
        snapshot = _snapshot_sqlite(connection, case["input"]["table"])
        return {
            "confirmed": snapshot == case["expected"],
            "snapshot": snapshot,
            "expected": copy.deepcopy(case["expected"]),
        }
    finally:
        connection.close()


def _candidate_transforms(m101_state: dict[str, Any]) -> list[str]:
    a_id, b_id = _m101_ids(m101_state)
    calls_a = [
        f"CALL:{a_id}:{left}:{right}"
        for left, right in itertools.product(range(4), repeat=2)
    ]
    calls_b = [
        f"CALL:{b_id}:{first}:{second}:{third}"
        for first, second, third in itertools.product(range(4), repeat=3)
    ]
    applies = [f"APPLY_SLOT:{index}" for index in range(4)]
    return applies + calls_a + calls_b


def acquire_c(
    state: dict[str, Any], demand: dict[str, Any], *, register_result: bool
) -> dict[str, Any]:
    checked = decode_state(state)
    public = decode_c_demand(demand)
    if checked["c_definition"] is not None:
        raise ValueError("C acquisition requires pre-C state")
    try:
        registry_index(checked)
    except ValueError:
        return {
            "schema": "m102-c-acquisition-v1",
            "confirmed": False,
            "reason": "joint registered descriptors are unrepresentable by the live policy",
            "assembled": 0,
            "well_formed": 0,
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "public_case_ids": [item["case_id"] for item in public["public_cases"]],
        }
    m101_state = m101_runtime.decode_state(checked["m101_ascii"].encode("ascii"))
    _a_id, b_id = _m101_ids(m101_state)
    slots = public["slots"]
    try:
        atomics = _resolved_sqlite_atomics(checked, slots)
    except (KeyError, ValueError):
        return {
            "schema": "m102-c-acquisition-v1",
            "confirmed": False,
            "reason": "joint registered SQLite descriptors are unavailable",
            "assembled": 0,
            "well_formed": 0,
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "public_case_ids": [item["case_id"] for item in public["public_cases"]],
        }

    transforms = _candidate_transforms(m101_state)
    assembled = 0
    well_formed = 0
    accepted: list[list[str]] = []
    for transform_count in range(1, C_MAX_TRANSFORMS + 1):
        for middle in itertools.product(transforms, repeat=transform_count):
            assembled += 1
            body = ["LOAD_INPUT", *middle, "RETURN"]
            trace = c_symbolic_trace(body, m101_state)
            if trace is None or any(index not in range(4) for index in trace):
                continue
            well_formed += 1
            try:
                if all(
                    execute_c_body(body, m101_state, case["input"], atomics) == case["expected"]
                    for case in public["public_cases"]
                ):
                    accepted.append(body)
            except Exception:
                continue
    accepted.sort(key=lambda body: (len(body), digest(body)))
    actually_confirmed: list[list[str]] = []
    for body in accepted:
        candidate = c_definition(body, b_id=b_id, policy_id=checked["policy"]["policy_id"])
        try:
            if all(
                execute_sqlite_case(checked, candidate, case, slots)["confirmed"]
                for case in public["public_cases"]
            ):
                actually_confirmed.append(body)
        except Exception:
            continue
    if not actually_confirmed:
        return {
            "schema": "m102-c-acquisition-v1",
            "confirmed": False,
            "assembled": assembled,
            "well_formed": well_formed,
            "model_accepted": len(accepted),
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "public_case_ids": [item["case_id"] for item in public["public_cases"]],
        }
    selected = actually_confirmed[0]
    adopted = c_definition(selected, b_id=b_id, policy_id=checked["policy"]["policy_id"])
    next_state = (
        decode_state(
            _state(
                checked["m101_ascii"].encode("ascii"),
                checked["policy"],
                checked["journal"],
                adopted,
            )
        )
        if register_result
        else None
    )
    return {
        "schema": "m102-c-acquisition-v1",
        "confirmed": True,
        "assembled": assembled,
        "well_formed": well_formed,
        "model_accepted": len(accepted),
        "accepted": len(actually_confirmed),
        "shortest_accepted_length": len(selected),
        "symbolic_trace": list(c_symbolic_trace(selected, m101_state) or ()),
        "adopted": adopted,
        "registered": bool(register_result),
        "next_state": next_state,
        "public_case_ids": [item["case_id"] for item in public["public_cases"]],
    }


def execute_c_world(state: dict[str, Any], demand: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    public = decode_c_demand(demand)
    if checked["c_definition"] is None:
        return {
            "schema": "m102-c-execution-v1",
            "confirmed": False,
            "reason": "C is absent",
            "passed": 0,
            "total": len(public["public_cases"]),
        }
    outcomes: list[dict[str, Any]] = []
    for case in public["public_cases"]:
        try:
            outcome = execute_sqlite_case(
                checked, checked["c_definition"], case, public["slots"]
            )
        except Exception as error:
            outcome = {
                "confirmed": False,
                "error_type": type(error).__name__,
                "snapshot": None,
                "expected": copy.deepcopy(case["expected"]),
            }
        outcomes.append({"case_id": case["case_id"], **outcome})
    passed = sum(bool(item["confirmed"]) for item in outcomes)
    return {
        "schema": "m102-c-execution-v1",
        "confirmed": passed == len(outcomes),
        "passed": passed,
        "total": len(outcomes),
        "outcomes": outcomes,
    }


def mutate_policy_to_flat(state: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    flat = inherited_flat_policy()
    c_item = None
    if checked["c_definition"] is not None:
        m101_state = m101_runtime.decode_state(checked["m101_ascii"].encode("ascii"))
        _a_id, b_id = _m101_ids(m101_state)
        c_item = c_definition(
            checked["c_definition"]["body"], b_id=b_id, policy_id=flat["policy_id"]
        )
    return decode_state(
        _state(
            checked["m101_ascii"].encode("ascii"), flat, checked["journal"], c_item
        )
    )


def ablate_policy_raw(state: dict[str, Any]) -> bytes:
    """Remove K without re-addressing C, producing a digest-valid fail-closed state."""
    checked = decode_state(state)
    return canonical_json(
        _state(
            checked["m101_ascii"].encode("ascii"),
            inherited_flat_policy(),
            checked["journal"],
            checked["c_definition"],
        )
    ).encode("ascii")


def mutate_c_duplicate_effect(state: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    if checked["c_definition"] is None:
        raise ValueError("C is required for mutation")
    body = list(checked["c_definition"]["body"])
    direct_index = next(
        index for index, token in enumerate(body) if token.startswith("APPLY_SLOT:")
    )
    body[direct_index] = "APPLY_SLOT:0"
    m101_state = m101_runtime.decode_state(checked["m101_ascii"].encode("ascii"))
    _a_id, b_id = _m101_ids(m101_state)
    mutated = c_definition(body, b_id=b_id, policy_id=checked["policy"]["policy_id"])
    return decode_state(
        _state(
            checked["m101_ascii"].encode("ascii"),
            checked["policy"],
            checked["journal"],
            mutated,
        )
    )


def mutate_m101_b_order(state: dict[str, Any]) -> dict[str, Any]:
    """Create a digest-valid live B semantic fault and re-address dependent C.

    B still has one live A call, one direct application and the complete distinct
    symbolic image.  Only the non-commuting execution order changes, so failure cannot
    be explained by a malformed or dead serialized dependency.
    """
    checked = decode_state(state)
    if checked["c_definition"] is None:
        raise ValueError("C is required for the live B mutation")
    predecessor = m101_runtime.decode_state(checked["m101_ascii"].encode("ascii"))
    a, b = copy.deepcopy(predecessor["definitions"])
    body = list(b["body"])
    call_index = next(index for index, token in enumerate(body) if token.startswith("CALL:"))
    call = _parse_call(body[call_index])
    if call is None or call[0] != a["definition_id"] or len(call[1]) != 2:
        raise ValueError("embedded B call shape is invalid")
    left, right = call[1]
    if left == right:
        raise ValueError("embedded B cannot be order-mutated")
    body[call_index] = f"CALL:{a['definition_id']}:{right}:{left}"
    mutated_b = m101_runtime.definition(
        m101_runtime.B_ORIGIN, body, [str(a["definition_id"])]
    )
    mutated_m101 = m101_runtime.decode_state(
        m101_runtime._state(
            predecessor["m100_ascii"].encode("ascii"), [a, mutated_b]
        )
    )
    mutated_m101_raw = m101_runtime.canonical_json(mutated_m101).encode("ascii")
    old_b_id = str(b["definition_id"])
    new_b_id = str(mutated_b["definition_id"])
    c_body = [
        token.replace(f"CALL:{old_b_id}:", f"CALL:{new_b_id}:")
        if token.startswith("CALL:")
        else token
        for token in checked["c_definition"]["body"]
    ]
    mutated_c = c_definition(
        c_body, b_id=new_b_id, policy_id=checked["policy"]["policy_id"]
    )
    return decode_state(
        _state(mutated_m101_raw, checked["policy"], checked["journal"], mutated_c)
    )


def ablate_m101_b_raw(state: dict[str, Any]) -> bytes:
    """Remove B while keeping outer M102 bytes internally content-addressed.

    The result is intentionally rejected by the M102 decoder because C cannot have a
    live B dependency.  Returning raw bytes allows a fresh consumer to demonstrate
    fail-closed removal without the producer relabelling the invalid state as valid.
    """
    checked = decode_state(state)
    predecessor = m101_runtime.decode_state(checked["m101_ascii"].encode("ascii"))
    without_b = m101_runtime.ablate_b(predecessor)
    predecessor_raw = m101_runtime.canonical_json(without_b).encode("ascii")
    return canonical_json(
        _state(
            predecessor_raw,
            checked["policy"],
            checked["journal"],
            checked["c_definition"],
        )
    ).encode("ascii")


def ablate_c(state: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    return decode_state(
        _state(
            checked["m101_ascii"].encode("ascii"),
            checked["policy"],
            checked["journal"],
            None,
        )
    )


def corrupt_state_digest(state: dict[str, Any]) -> bytes:
    checked = decode_state(state)
    corrupted = copy.deepcopy(checked)
    old = str(corrupted["state_digest"])
    corrupted["state_digest"] = ("0" if old[0] != "0" else "1") + old[1:]
    return canonical_json(corrupted).encode("ascii")


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    m101_state = m101_runtime.decode_state(checked["m101_ascii"].encode("ascii"))
    return {
        "state_digest": checked["state_digest"],
        "raw_sha256": sha256_bytes(encode_state(checked)),
        "m101_sha256": checked["m101_sha256"],
        "m101_definition_ids": [item["definition_id"] for item in m101_state["definitions"]],
        "policy_id": checked["policy"]["policy_id"],
        "policy_origin": checked["policy"]["origin"],
        "event_count": len(checked["journal"]),
        "event_ids": [item["event_id"] for item in checked["journal"]],
        "c_definition_id": (
            checked["c_definition"]["definition_id"]
            if checked["c_definition"] is not None
            else None
        ),
    }


def runtime_identity() -> dict[str, Any]:
    return {
        "python_sqlite_module": sqlite3.__name__,
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite_version_info": list(sqlite3.sqlite_version_info),
    }
