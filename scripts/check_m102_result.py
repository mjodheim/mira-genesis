"""Independently recompute M102's frozen fifteen-condition verdict."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M102"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"
CHECKER_EPHEMERAL_KEYS = {
    "pid",
    "process_pids",
    "search_path",
    "elapsed_seconds",
    "started_at_utc",
}
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

from audit_m102_boundaries import audit as audit_boundaries
from author_m102_qualification_pool import audit as audit_pool
from author_m102_qualification_pool import build_pool, canonical_json, digest, load_pool
from check_m102_definitions import validate as validate_definitions
from run_m102_qualification import (
    CAPSULE_SOURCES,
    capsule_binding,
    file_set_digest,
    m101_t2_bytes,
    require_frozen,
    run_experiment,
)


def checker_stable_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: checker_stable_projection(item)
            for key, item in value.items()
            if key not in CHECKER_EPHEMERAL_KEYS
        }
    if isinstance(value, list):
        return [checker_stable_projection(item) for item in value]
    return value


@dataclass(frozen=True)
class Condition:
    identifier: str
    name: str
    computed: bool
    passed: bool | None
    failures: list[str]
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "computed": self.computed,
            "passed": self.passed,
            "failures": self.failures,
            "evidence": self.evidence,
        }


def _condition(
    identifier: str,
    name: str,
    failures: list[str],
    evidence: dict[str, Any] | None = None,
) -> Condition:
    return Condition(identifier, name, True, not failures, failures, evidence or {})


def _uncomputed(identifier: str, name: str, error: str) -> Condition:
    return Condition(identifier, name, False, None, [error], {})


def _success(row: dict[str, Any]) -> bool:
    return row.get("returncode") == 0 and row.get("runtime", {}).get("confirmed") is True


def _failure(row: dict[str, Any]) -> bool:
    return row.get("returncode") != 0 and row.get("runtime", {}).get("confirmed") is False


def _state_bytes(record: dict[str, Any]) -> bytes:
    raw = canonical_json(record["state"]).encode("ascii")
    if hashlib.sha256(raw).hexdigest() != record["raw_sha256"]:
        raise ValueError("recorded M102 state bytes do not match their raw digest")
    return raw


def _policy_output(body: list[str], carrier: str, slot: str) -> Any:
    stack: list[Any] = []
    returned = False
    result: Any = None
    for token in body:
        if returned:
            raise ValueError("policy continues after return")
        if token == "LOAD_CARRIER":
            stack.append(carrier)
        elif token == "LOAD_SLOT":
            stack.append(slot)
        elif token == "PAIR":
            if len(stack) < 2:
                raise ValueError("policy pair underflow")
            right = stack.pop()
            left = stack.pop()
            stack.append([left, right])
        elif token == "DUP":
            if not stack:
                raise ValueError("policy duplicate underflow")
            stack.append(copy.deepcopy(stack[-1]))
        elif token == "SWAP":
            if len(stack) < 2:
                raise ValueError("policy swap underflow")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif token == "RETURN":
            if len(stack) != 1:
                raise ValueError("policy return arity changed")
            result = stack.pop()
            returned = True
        else:
            raise ValueError("policy instruction is invalid")
    if not returned or stack:
        raise ValueError("policy did not return exactly one key")
    return result


def _registry(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policy = state["policy"]
    index: dict[str, dict[str, Any]] = {}
    for event in state["journal"]:
        key = canonical_json(_policy_output(policy["body"], event["carrier"], event["slot"]))
        descriptor = copy.deepcopy(event["descriptor"])
        if key in index and index[key] != descriptor:
            raise ValueError("independent registry reconstruction found an unequal collision")
        index[key] = descriptor
    return index


def _resolve(state: dict[str, Any], carrier: str, slot: str) -> dict[str, Any]:
    key = canonical_json(_policy_output(state["policy"]["body"], carrier, slot))
    index = _registry(state)
    if key not in index:
        raise ValueError(f"independent registry lookup is absent: {carrier}/{slot}")
    return copy.deepcopy(index[key])


def _flat_closure(state: dict[str, Any], incoming: list[dict[str, Any]]) -> dict[str, Any]:
    if state["policy"]["body"] != ["LOAD_SLOT", "RETURN"]:
        raise ValueError("flat closure received a non-flat predecessor")
    groups: dict[str, list[dict[str, Any]]] = {}
    for event in [*state["journal"], *incoming]:
        key = canonical_json(event["slot"])
        groups.setdefault(key, []).append(event)
    witnesses = []
    for key, events in sorted(groups.items()):
        descriptor_digests = sorted({digest(event["descriptor"]) for event in events})
        if len(descriptor_digests) > 1:
            witnesses.append(
                {
                    "key": key,
                    "event_ids": sorted(event["event_id"] for event in events),
                    "descriptor_digests": descriptor_digests,
                }
            )
    return {
        "event_count": sum(len(events) for events in groups.values()),
        "distinct_output_keys": len(groups),
        "collision_witnesses": witnesses,
        "joint_relation_representable": not witnesses,
        "budget_independent": True,
    }


def _parse_call(token: str) -> tuple[str, tuple[int, ...]] | None:
    if not token.startswith("CALL:"):
        return None
    parts = token.split(":")
    try:
        return parts[1], tuple(int(item) for item in parts[2:])
    except (IndexError, ValueError):
        return None


def _a_order(body: list[str], slots: tuple[int, int]) -> tuple[int, ...]:
    stack: list[tuple[int, ...]] = []
    result: tuple[int, ...] | None = None
    for token in body:
        if token == "LOAD_INPUT":
            stack.append(())
        elif token == "APPLY_SLOT:0" and stack:
            stack.append(stack.pop() + (slots[0],))
        elif token == "APPLY_SLOT:1" and stack:
            stack.append(stack.pop() + (slots[1],))
        elif token == "DUP" and stack:
            stack.append(stack[-1])
        elif token == "SWAP" and len(stack) >= 2:
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif token == "RETURN" and len(stack) == 1:
            result = stack.pop()
        else:
            raise ValueError("independent A symbolic execution failed")
    if result is None or stack:
        raise ValueError("independent A symbolic return failed")
    return result


def _b_order(
    body: list[str], a_id: str, a_body: list[str], slots: tuple[int, int, int]
) -> tuple[int, ...]:
    current: tuple[int, ...] | None = None
    returned = False
    for token in body:
        if token == "LOAD_INPUT" and current is None:
            current = ()
        elif token.startswith("CALL:") and current is not None:
            call = _parse_call(token)
            if call is None or call[0] != a_id or len(call[1]) != 2:
                raise ValueError("independent B call failed")
            current += _a_order(a_body, (slots[call[1][0]], slots[call[1][1]]))
        elif token.startswith("APPLY_SLOT:") and current is not None:
            current += (slots[int(token.split(":", 1)[1])],)
        elif token == "RETURN" and current is not None:
            returned = True
        else:
            raise ValueError("independent B symbolic execution failed")
    if not returned or current is None:
        raise ValueError("independent B symbolic return failed")
    return current


def _c_order(state: dict[str, Any]) -> tuple[int, ...]:
    predecessor = json.loads(state["m101_ascii"])
    a, b = predecessor["definitions"]
    c_item = state["c_definition"]
    if c_item is None:
        raise ValueError("C is absent")
    order: tuple[int, ...] = ()
    for token in c_item["body"][1:-1]:
        call = _parse_call(token)
        if call is not None:
            if call[0] != b["definition_id"] or len(call[1]) != 3:
                raise ValueError("C does not execute live B")
            order += _b_order(
                b["body"],
                a["definition_id"],
                a["body"],
                (call[1][0], call[1][1], call[1][2]),
            )
        else:
            order += (int(token.split(":", 1)[1]),)
    if sorted(order) != [0, 1, 2, 3]:
        raise ValueError("independent C order is not four complete effects")
    return order


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError("unsafe SQLite identifier")
    return value


def _quote(value: Any) -> str:
    return f'"{_identifier(value)}"'


def _literal(value: Any) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise ValueError("invalid SQLite literal")


def _materialize(model: dict[str, Any]) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    table = _quote(model["table"])
    connection.execute(
        f"CREATE TABLE {table} ("
        + ",".join(f"{_quote(item['name'])} {item['type']}" for item in model["columns"])
        + ")"
    )
    names = [item["name"] for item in model["columns"]]
    for row in model["rows"]:
        connection.execute(
            f"INSERT INTO {table} ({','.join(_quote(name) for name in names)}) "
            f"VALUES ({','.join('?' for _ in names)})",
            tuple(row[name] for name in names),
        )
    for index in model["indexes"]:
        connection.execute(
            f"CREATE INDEX {_quote(index['name'])} ON {table} "
            f"({','.join(_quote(name) for name in index['columns'])})"
        )
    connection.commit()
    return connection


def _apply_descriptor(connection: sqlite3.Connection, descriptor: dict[str, Any]) -> None:
    kind = descriptor["kind"]
    if kind == "add_column":
        column_type = descriptor["type"]
        if column_type not in {"INTEGER", "TEXT"}:
            raise ValueError("invalid SQLite add type")
        connection.execute(
            f"ALTER TABLE {_quote(descriptor['table'])} "
            f"ADD COLUMN {_quote(descriptor['column'])} {column_type} "
            f"DEFAULT {_literal(descriptor['default'])}"
        )
    elif kind == "backfill_length":
        connection.execute(
            f"UPDATE {_quote(descriptor['table'])} "
            f"SET {_quote(descriptor['target'])}=length({_quote(descriptor['source'])})"
        )
    elif kind == "rename_column":
        connection.execute(
            f"ALTER TABLE {_quote(descriptor['table'])} "
            f"RENAME COLUMN {_quote(descriptor['old'])} TO {_quote(descriptor['new'])}"
        )
    elif kind == "create_index":
        connection.execute(
            f"CREATE INDEX {_quote(descriptor['name'])} ON {_quote(descriptor['table'])} "
            f"({','.join(_quote(name) for name in descriptor['columns'])})"
        )
    else:
        raise ValueError("unknown SQLite effect descriptor")
    connection.commit()


def _snapshot(connection: sqlite3.Connection, table: str) -> dict[str, Any]:
    columns = [
        {"name": row[1], "type": str(row[2]).upper()}
        for row in connection.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
    ]
    names = [item["name"] for item in columns]
    rows = [
        dict(zip(names, row, strict=True))
        for row in connection.execute(
            f"SELECT {','.join(_quote(name) for name in names)} FROM {_quote(table)} "
            f"ORDER BY {_quote(names[0])}"
        ).fetchall()
    ]
    indexes = []
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
        raise ValueError("independent SQLite integrity check failed")
    return {"table": table, "columns": columns, "rows": rows, "indexes": indexes}


def _independent_sqlite(
    state: dict[str, Any], world: dict[str, Any]
) -> list[dict[str, Any]]:
    order = _c_order(state)
    descriptors = [_resolve(state, "sqlite", slot) for slot in world["slots"]]
    outcomes = []
    for case in world["public_cases"] + world["hidden_cases"]:
        connection = _materialize(case["input"])
        try:
            for index in order:
                _apply_descriptor(connection, descriptors[index])
            snapshot = _snapshot(connection, case["input"]["table"])
        finally:
            connection.close()
        outcomes.append(
            {
                "case_id": case["case_id"],
                "passed": snapshot == case["expected"],
                "snapshot": snapshot,
                "expected": case["expected"],
            }
        )
    return outcomes


def _worlds(pool: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    worlds = [entry["world"] for entry in pool["entries"]]
    return worlds, {world["id"]: world for world in worlds}


def check_p1(protocol: dict[str, Any], pool: dict[str, Any]) -> Condition:
    failures: list[str] = []
    try:
        require_frozen(protocol, pool)
    except Exception as error:
        failures.append(str(error))
    boundary = audit_boundaries()
    if boundary.get("passed") is not True:
        failures.append("frozen boundary audit is not clean")
    for name, sources in CAPSULE_SOURCES.items():
        measured, members = capsule_binding(sources)
        declared = protocol.get("capsules", {}).get(name, {})
        if declared.get("digest") != measured or declared.get("member_digests") != members:
            failures.append(f"{name} capsule binding moved")
    for section in ("mechanism", "qualification_apparatus", "checker"):
        declared = protocol.get(section, {})
        measured, members = file_set_digest(list(declared.get("files", [])))
        if declared.get("digest") != measured or declared.get("member_digests") != members:
            failures.append(f"{section} source binding moved")
    return _condition("P1", "frozen_bindings", failures, {"boundary_audit": boundary})


def check_p2(pool: dict[str, Any]) -> Condition:
    failures: list[str] = []
    preflight = audit_pool(pool)
    rebuilt = build_pool(status="frozen")
    if pool != rebuilt:
        failures.append("frozen pool differs from source-only authored population")
    if preflight.get("passed") is not True or preflight.get("entries_checked") != 13:
        failures.append("population source preflight is not clean")
    if preflight.get("hidden_success_was_scored") is not False:
        failures.append("preflight scored hidden success")
    return _condition("P2", "clean_population", failures, preflight)


def check_p3(result: dict[str, Any], evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    predecessor_raw, predecessor_state = m101_t2_bytes()
    states = evidence.get("states", {})
    for name in ("U0", "U1", "PRE_C", "U2"):
        record = states.get(name, {})
        state = record.get("state", {})
        if state.get("m101_ascii", "").encode("ascii") != predecessor_raw:
            failures.append(f"{name} does not contain exact M101 T2 bytes")
        try:
            validate_definitions(
                _state_bytes(record),
                expected_m101_sha256=hashlib.sha256(predecessor_raw).hexdigest(),
                expected_m100_sha256=predecessor_state["m100_sha256"],
            )
        except Exception as error:
            failures.append(f"{name} independent definition validation failed: {error}")
    if not all(_success(row["fresh"]) for row in evidence.get("m101_conservation", [])):
        failures.append("M101 A/B conservation failed")
    if not all(_success(row["fresh"]) for row in evidence.get("m100_conservation", [])):
        failures.append("M100 conservation failed")
    if result.get("model_calls") != 0:
        failures.append("result records external model calls")
    return _condition(
        "P3",
        "exact_predecessor",
        failures,
        {"m101_t2_raw_sha256": hashlib.sha256(predecessor_raw).hexdigest()},
    )


def check_p4(evidence: dict[str, Any], world_by_id: dict[str, dict[str, Any]]) -> Condition:
    failures: list[str] = []
    u0 = evidence["states"]["U0"]["state"]
    policy_world = next(
        world for world in world_by_id.values() if world["role"] == "policy_producer_trigger"
    )
    closure = _flat_closure(u0, policy_world["incoming_events"])
    recorded = evidence.get("interference", {}).get("flat_closure")
    if closure != {key: recorded.get(key) for key in closure}:
        failures.append("recorded flat closure differs from independent closure")
    if closure["joint_relation_representable"] is not False or not closure["collision_witnesses"]:
        failures.append("flat policy did not prove a structural unequal collision")
    c_without_k = evidence["state_chronology"]["c_absent_without_k_reach"]
    if not _failure(c_without_k):
        failures.append("C unexpectedly acquired on the no-K joint state")
    if "unrepresentable" not in str(
        c_without_k.get("runtime", {}).get("acquisition", {}).get("reason", "")
    ):
        failures.append("no-K failure is not caused by registry representability")
    return _condition("P4", "inherited_insufficiency", failures, closure)


def check_p5(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    acquisition = evidence["state_chronology"]["acquire_and_register_k"]
    payload = acquisition.get("runtime", {}).get("acquisition", {})
    report = evidence.get("definition_validation", {}).get("U1", {}).get("runtime", {})
    if not _success(acquisition) or payload.get("assembled") != sum(6**n for n in range(1, 5)):
        failures.append("K was not exhaustively acquired and registered")
    adopted = payload.get("adopted", {})
    text = canonical_json(adopted).lower()
    if adopted.get("origin") != "m102-acquired-policy" or any(
        term in text for term in ("sqlite", "record", "namespace", "solution")
    ):
        failures.append("K is target-specific or has wrong provenance")
    policy_report = report.get("policy", {})
    if (
        report.get("confirmed") is not True
        or policy_report.get("policy_id") != adopted.get("policy_id")
        or policy_report.get("carrier_input_causal") is not True
        or policy_report.get("slot_input_causal") is not True
    ):
        failures.append("independent K validation failed")
    return _condition("P5", "endogenous_k_acquisition", failures, payload)


def check_p6(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    chronology = evidence["state_chronology"]
    built = chronology["k_built_not_registered"]
    if not _success(built) or built.get("runtime", {}).get("acquisition", {}).get("registered"):
        failures.append("building K without registration did not remain non-adoptive")
    if chronology.get("u0_unchanged_after_k_build") is not True:
        failures.append("U0 changed after unregistered K construction")
    if not _success(chronology["acquire_and_register_k"]):
        failures.append("registered K transition failed")
    if evidence["states"].get("u0_u1_differing_keys") != ["journal", "policy", "state_digest"]:
        failures.append("U0/U1 changed outside policy adoption, incoming journal and digest")
    return _condition("P6", "registration_causality", failures)


def check_p7(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    rows = evidence.get("interference", {}).get("retained_after_u1", [])
    if len(rows) != 3 or not all(_success(row["fresh"]) for row in rows):
        failures.append("K did not retain all three earlier record capabilities after producer death")
    try:
        index = _registry(evidence["states"]["U1"]["state"])
        if len(index) != evidence["states"]["U1"]["event_count"]:
            failures.append("U1 registry does not reconstruct uniquely from K plus journal")
    except Exception as error:
        failures.append(f"U1 registry reconstruction failed: {error}")
    return _condition("P7", "hard_persistence", failures)


def check_p8(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    destructive = evidence.get("interference", {}).get("destructive_no_upgrade", [])
    if len(destructive) != 3 or all(_success(row["fresh"]) for row in destructive):
        failures.append("destructive no-upgrade arm forgot no earlier capability")
    if not _failure(evidence["state_chronology"]["flat_registration_fails_closed"]):
        failures.append("flat fail-closed control accepted incompatible bindings")
    closure = evidence.get("interference", {}).get("flat_closure", {})
    if closure.get("budget_independent") is not True:
        failures.append("more-budget flat impossibility is not structural")
    return _condition(
        "P8",
        "real_interference",
        failures,
        {"destructive_successes": sum(_success(row["fresh"]) for row in destructive)},
    )


def check_p9(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    chronology = evidence["state_chronology"]
    built = chronology["c_built_not_registered"]
    adopted = chronology["acquire_and_register_c"]
    if not _success(built) or not _success(adopted):
        failures.append("C was not behaviorally acquired both before and at registration")
    if chronology.get("pre_c_unchanged_after_c_build") is not True:
        failures.append("pre-C state changed during unregistered C construction")
    payload = adopted.get("runtime", {}).get("acquisition", {})
    if payload.get("assembled", 0) <= 7000 or sorted(payload.get("symbolic_trace", [])) != [0, 1, 2, 3]:
        failures.append("C search/trace evidence is incomplete")
    boundary = evidence.get("information_boundary", {})
    if set(boundary.get("c_acquisition_received_only_public_case_ids", [])) & set(
        boundary.get("c_hidden_case_ids", [])
    ):
        failures.append("C public and hidden case ids overlap")
    report = evidence.get("definition_validation", {}).get("U2", {}).get("runtime", {})
    if report.get("c_definition", {}).get("live_b_calls") != 1:
        failures.append("independent C validation did not find exactly one live B call")
    return _condition("P9", "demand_derived_c", failures, payload)


def check_p10(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    controls = evidence.get("causal_controls", {}).get("c_executions", {})
    for label in ("flat_policy", "policy_ablation", "b_mutation", "b_ablation"):
        if not _failure(controls.get(label, {})):
            failures.append(f"{label} did not break C")
    u2 = evidence["states"]["U2"]["state"]
    c_item = u2["c_definition"]
    predecessor = json.loads(u2["m101_ascii"])
    if c_item.get("policy_dependency") != u2["policy"]["policy_id"]:
        failures.append("C does not address live K")
    if c_item.get("definition_dependencies") != [predecessor["definitions"][1]["definition_id"]]:
        failures.append("C does not address live M101 B")
    return _condition("P10", "live_cumulative_dependency", failures)


def check_p11(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    groups = {
        "record": [row["fresh"] for row in evidence.get("continual_retention_after_u2", [])],
        "m101": [row["fresh"] for row in evidence.get("m101_conservation", [])],
        "m100": [row["fresh"] for row in evidence.get("m100_conservation", [])],
    }
    expected = {"record": 3, "m101": 2, "m100": 3}
    for label, rows in groups.items():
        if len(rows) != expected[label] or not all(_success(row) for row in rows):
            failures.append(f"{label} capabilities were not completely retained after C")
    return _condition(
        "P11",
        "continual_retention",
        failures,
        {"retained_counts": {label: len(rows) for label, rows in groups.items()}},
    )


def check_p12(
    evidence: dict[str, Any], world_by_id: dict[str, dict[str, Any]]
) -> Condition:
    failures: list[str] = []
    rows = evidence.get("sqlite_execution", [])
    if len(rows) != 4 or not all(_success(row["fresh"]) for row in rows):
        failures.append("C did not pass trigger plus all three SQLite reuse worlds")
    state = evidence["states"]["U2"]["state"]
    independent_case_count = 0
    for row in rows:
        world = world_by_id[row["entry"]]
        try:
            independent = _independent_sqlite(state, world)
        except Exception as error:
            failures.append(f"independent SQLite execution failed for {row['entry']}: {error}")
            continue
        independent_case_count += len(independent)
        recorded = row["fresh"].get("runtime", {}).get("execution", {}).get("outcomes", [])
        recorded_by_id = {item.get("case_id"): item for item in recorded}
        for outcome in independent:
            observed = recorded_by_id.get(outcome["case_id"], {})
            if outcome["passed"] is not True or observed.get("snapshot") != outcome["snapshot"]:
                failures.append(f"SQLite state mismatch for {outcome['case_id']}")
    if independent_case_count != 32:
        failures.append("independent SQLite checker did not inspect all 32 cases")
    return _condition(
        "P12",
        "real_sqlite_state",
        failures,
        {"independently_inspected_cases": independent_case_count},
    )


def check_p13(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    boundary = evidence.get("process_boundary", {})
    required = (
        "pid_records_present",
        "all_invocation_ordinals_unique_and_contiguous",
        "synchronous_process_exit_before_next_launch",
        "fresh_subprocess_launch_source_audited",
        "all_invocations_isolated",
        "no_project_modules_imported",
        "repository_absent_from_search_paths",
        "zero_model_calls",
        "zero_network_calls",
        "zero_remote_execution_calls",
    )
    for name in required:
        if boundary.get(name) is not True:
            failures.append(f"process/authority boundary failed: {name}")
    if evidence.get("boundary_audit", {}).get("passed") is not True:
        failures.append("source boundary audit failed")
    return _condition("P13", "isolated_authority", failures, boundary)


def check_p14(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    causal = evidence.get("causal_controls", {})
    if not all(_success(row) for row in causal.get("builds", {}).values()):
        failures.append("one or more causal control states were not materialised")
    if not all(_failure(row) for row in causal.get("c_executions", {}).values()):
        failures.append("one or more faulted states did not suppress C")
    if not all(_success(row) for row in causal.get("unrelated_capabilities", {}).values()):
        failures.append("a selective unrelated capability control failed")
    rollback = evidence.get("rollback", {})
    if (
        rollback.get("fault_differs_from_accepted") is not True
        or rollback.get("restored_bytes_equal") is not True
        or rollback.get("restored_raw_sha256") != rollback.get("accepted_raw_sha256")
        or not _success(rollback.get("restore_process", {}))
    ):
        failures.append("exact rollback bytes/process failed")
    for group, expected in (("record", 3), ("sqlite", 4), ("m101", 2), ("m100", 3)):
        rows = rollback.get(group, [])
        if len(rows) != expected or not all(_success(row) for row in rows):
            failures.append(f"rollback did not restore full {group} capability set")
    return _condition("P14", "causal_controls_and_rollback", failures)


def check_p15(
    result: dict[str, Any], evidence: dict[str, Any], pool: dict[str, Any]
) -> Condition:
    failures: list[str] = []
    if result.get("attempt") != 1 or result.get("canonical") is not True or result.get("reroll") is not False:
        failures.append("result is not the unique canonical attempt 1")
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(payload):
        failures.append("result digest is internally invalid")
    stable = digest(checker_stable_projection(evidence))
    if result.get("stable_evidence_digest") != stable:
        failures.append("recorded stable evidence digest differs from checker projection")
    replay = run_experiment(pool, allow_frozen=True)
    replay_digest = digest(checker_stable_projection(replay))
    if replay_digest != stable:
        failures.append("clean replay differs from first stable evidence")
    return _condition(
        "P15",
        "stable_first_attempt",
        failures,
        {"recorded_stable_digest": stable, "replay_stable_digest": replay_digest},
    )


CONDITION_NAMES = {
    "P1": "frozen_bindings",
    "P2": "clean_population",
    "P3": "exact_predecessor",
    "P4": "inherited_insufficiency",
    "P5": "endogenous_k_acquisition",
    "P6": "registration_causality",
    "P7": "hard_persistence",
    "P8": "real_interference",
    "P9": "demand_derived_c",
    "P10": "live_cumulative_dependency",
    "P11": "continual_retention",
    "P12": "real_sqlite_state",
    "P13": "isolated_authority",
    "P14": "causal_controls_and_rollback",
    "P15": "stable_first_attempt",
}


def check(result: dict[str, Any], protocol: dict[str, Any], pool: dict[str, Any]) -> dict[str, Any]:
    evidence = result.get("scientific_evidence", {})
    _world_list, world_by_id = _worlds(pool)
    functions = [
        lambda: check_p1(protocol, pool),
        lambda: check_p2(pool),
        lambda: check_p3(result, evidence),
        lambda: check_p4(evidence, world_by_id),
        lambda: check_p5(evidence),
        lambda: check_p6(evidence),
        lambda: check_p7(evidence),
        lambda: check_p8(evidence),
        lambda: check_p9(evidence),
        lambda: check_p10(evidence),
        lambda: check_p11(evidence),
        lambda: check_p12(evidence, world_by_id),
        lambda: check_p13(evidence),
        lambda: check_p14(evidence),
        lambda: check_p15(result, evidence, pool),
    ]
    conditions: list[Condition] = []
    for index, function in enumerate(functions, start=1):
        identifier = f"P{index}"
        try:
            condition = function()
        except Exception as error:
            condition = _uncomputed(
                identifier,
                CONDITION_NAMES[identifier],
                f"{type(error).__name__}: {error}",
            )
        conditions.append(condition)
    passed = sum(condition.passed is True for condition in conditions)
    failed = sum(condition.passed is False for condition in conditions)
    uncomputed = sum(not condition.computed for condition in conditions)
    verdict = "positive" if passed == 15 and failed == 0 and uncomputed == 0 else "negative"
    report: dict[str, Any] = {
        "schema": "m102-check-report-v1",
        "milestone": "M102",
        "attempt": result.get("attempt"),
        "verdict": verdict,
        "passed": passed,
        "failed": failed,
        "uncomputed": uncomputed,
        "conditions": {condition.identifier: condition.as_dict() for condition in conditions},
        "result_digest": result.get("result_digest"),
        "stable_evidence_digest": result.get("stable_evidence_digest"),
        "claim_boundary": (
            "bounded continual interference and registry meta-improvement mechanism evidence "
            "under an independently maintained SQLite execution interface only"
        ),
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    pool = load_pool()
    report = check(result, protocol, pool)
    if arguments.write:
        if CHECK_PATH.exists():
            raise FileExistsError("M102 checker report already exists")
        CHECK_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
