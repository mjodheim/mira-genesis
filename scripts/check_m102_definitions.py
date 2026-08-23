"""Independently validate M102 lineage-state definitions and registry structure.

This apparatus checker imports neither M102 implementation module.  It recomputes
canonical addresses, executes the registered policy over opaque probes, rebuilds the
registry solely from the journal, and symbolically evaluates C.  It delegates only the
embedded predecessor check to the already independent M101 definition checker.

It does not inspect qualification data and cannot issue a scientific verdict.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from scripts import check_m101_definitions as m101_checker
except ImportError:  # pragma: no cover - direct script execution
    import check_m101_definitions as m101_checker  # type: ignore[no-redef]


STATE_SCHEMA = "m102-lineage-state-v1"
POLICY_SCHEMA = "m102-registry-policy-v1"
EVENT_SCHEMA = "m102-registry-event-v1"
C_SCHEMA = "m102-cumulative-definition-v1"
REPORT_SCHEMA = "m102-definition-validation-v1"

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


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _policy_address(origin: str, body: list[str]) -> str:
    payload = {"schema": POLICY_SCHEMA, "origin": origin, "body": body}
    prefix = "registry-flat" if origin == FLAT_ORIGIN else "registry-policy"
    return f"{prefix}-{digest(payload)[:16]}"


def _interpret_policy(body: list[str], carrier: str, slot: str) -> Any:
    values: list[Any] = []
    result: Any = None
    complete = False
    for instruction in body:
        if complete:
            raise ValueError("policy continues after return")
        if instruction == "LOAD_CARRIER":
            values.append(carrier)
        elif instruction == "LOAD_SLOT":
            values.append(slot)
        elif instruction == "PAIR":
            if len(values) < 2:
                raise ValueError("policy pair underflow")
            second = values.pop()
            first = values.pop()
            values.append([first, second])
        elif instruction == "DUP":
            if not values:
                raise ValueError("policy duplicate underflow")
            values.append(copy.deepcopy(values[-1]))
        elif instruction == "SWAP":
            if len(values) < 2:
                raise ValueError("policy swap underflow")
            values[-2], values[-1] = values[-1], values[-2]
        elif instruction == "RETURN":
            if len(values) != 1:
                raise ValueError("policy return arity changed")
            result = values.pop()
            complete = True
        else:
            raise ValueError("policy contains an unknown instruction")
    if not complete or values:
        raise ValueError("policy has no exact return")
    return result


def _validate_policy(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    item = _closed(
        copy.deepcopy(raw),
        {"schema", "policy_id", "origin", "body"},
        "M102 policy",
    )
    if item["schema"] != POLICY_SCHEMA:
        raise ValueError("M102 policy schema mismatch")
    if item["origin"] not in {FLAT_ORIGIN, ACQUIRED_POLICY_ORIGIN}:
        raise ValueError("M102 policy origin is invalid")
    if not isinstance(item["body"], list) or not 1 <= len(item["body"]) <= 4 or not all(
        isinstance(instruction, str) for instruction in item["body"]
    ):
        raise ValueError("M102 policy body is invalid")
    if item["policy_id"] != _policy_address(str(item["origin"]), list(item["body"])):
        raise ValueError("M102 policy content address mismatch")
    if item["origin"] == FLAT_ORIGIN and item["body"] != ["LOAD_SLOT", "RETURN"]:
        raise ValueError("M102 inherited flat policy changed")
    if item["origin"] == ACQUIRED_POLICY_ORIGIN:
        lowered = canonical_json(item).lower()
        if any(term in lowered for term in FORBIDDEN_POLICY_SUBSTRINGS):
            raise ValueError("M102 acquired policy contains target-specific identity")

    probe = {
        "a_x": _interpret_policy(item["body"], "carrier_a", "slot_x"),
        "b_x": _interpret_policy(item["body"], "carrier_b", "slot_x"),
        "a_y": _interpret_policy(item["body"], "carrier_a", "slot_y"),
    }
    carrier_causal = probe["a_x"] != probe["b_x"]
    slot_causal = probe["a_x"] != probe["a_y"]
    if item["origin"] == ACQUIRED_POLICY_ORIGIN and not (carrier_causal and slot_causal):
        raise ValueError("M102 acquired policy does not retain both generic key inputs")
    report = {
        "policy_id": item["policy_id"],
        "origin": item["origin"],
        "body": list(item["body"]),
        "carrier_input_causal": carrier_causal,
        "slot_input_causal": slot_causal,
        "probe_outputs_digest": digest(probe),
    }
    return item, report


def _validate_event(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {"schema", "event_id", "carrier", "slot", "descriptor"},
        "M102 event",
    )
    if item["schema"] != EVENT_SCHEMA:
        raise ValueError("M102 event schema mismatch")
    if not isinstance(item["carrier"], str) or not item["carrier"]:
        raise ValueError("M102 event carrier is invalid")
    if not isinstance(item["slot"], str) or not item["slot"]:
        raise ValueError("M102 event slot is invalid")
    if not isinstance(item["descriptor"], dict) or not isinstance(
        item["descriptor"].get("kind"), str
    ):
        raise ValueError("M102 event descriptor is invalid")
    payload = {
        "schema": EVENT_SCHEMA,
        "carrier": item["carrier"],
        "slot": item["slot"],
        "descriptor": item["descriptor"],
    }
    if item["event_id"] != f"registry-event-{digest(payload)[:16]}":
        raise ValueError("M102 event content address mismatch")
    return item


def _rebuild_registry(
    policy: dict[str, Any], journal: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    index: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for event in journal:
        key_value = _interpret_policy(policy["body"], event["carrier"], event["slot"])
        key = canonical_json(key_value)
        descriptor = copy.deepcopy(event["descriptor"])
        if key in index and index[key] != descriptor:
            raise ValueError("M102 state policy aliases unequal journal descriptors")
        index[key] = descriptor
        rows.append(
            {
                "event_id": event["event_id"],
                "key": key_value,
                "key_digest": hashlib.sha256(key.encode("ascii")).hexdigest(),
                "descriptor_digest": digest(descriptor),
            }
        )
    return index, rows


def _parse_call(token: str) -> tuple[str, tuple[int, ...]] | None:
    if not token.startswith("CALL:"):
        return None
    pieces = token.split(":")
    if len(pieces) < 4:
        return None
    try:
        return pieces[1], tuple(int(piece) for piece in pieces[2:])
    except ValueError:
        return None


def _validate_c(
    raw: Any, *, a_id: str, b_id: str, policy_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
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
    if item["definition_dependencies"] != [b_id]:
        raise ValueError("M102 C declared dependency is not exactly live B")
    if item["policy_dependency"] != policy_id:
        raise ValueError("M102 C policy dependency is not the live policy")
    body = list(item["body"])
    if len(body) != 4 or body[0] != "LOAD_INPUT" or body[-1] != "RETURN":
        raise ValueError("M102 C does not have the required bounded shape")
    trace: list[int] = []
    calls = 0
    direct = 0
    live_b_calls = 0
    for token in body[1:-1]:
        call = _parse_call(token)
        if call is not None:
            calls += 1
            dependency, indices = call
            if dependency == a_id and len(indices) == 2:
                trace.extend(indices)
            elif dependency == b_id and len(indices) == 3:
                trace.extend(indices)
                live_b_calls += 1
            else:
                raise ValueError("M102 C calls an invalid or arity-mismatched dependency")
        elif token.startswith("APPLY_SLOT:"):
            try:
                trace.append(int(token.split(":", 1)[1]))
            except ValueError as error:
                raise ValueError("M102 C direct slot is invalid") from error
            direct += 1
        else:
            raise ValueError("M102 C contains an unknown instruction")
    if calls != 1 or direct != 1 or live_b_calls != 1:
        raise ValueError("M102 C does not execute exactly one live B call and one direct effect")
    if sorted(trace) != [0, 1, 2, 3]:
        raise ValueError("M102 C does not cover four distinct opaque effects")
    address_payload = {
        "schema": C_SCHEMA,
        "origin": C_ORIGIN,
        "body": body,
        "definition_dependencies": [b_id],
        "policy_dependency": policy_id,
    }
    expected_id = f"sqlite-successor-{digest(address_payload)[:16]}"
    if item["definition_id"] != expected_id:
        raise ValueError("M102 C content address mismatch")
    report = {
        "definition_id": item["definition_id"],
        "origin": item["origin"],
        "symbolic_trace": trace,
        "complete_distinct_trace": True,
        "live_b_calls": live_b_calls,
        "direct_applications": direct,
        "definition_dependencies": [b_id],
        "policy_dependency": policy_id,
    }
    return item, report


def validate(
    raw: bytes,
    *,
    expected_m101_sha256: str | None = None,
    expected_m100_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        state = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"M102 state is not canonical ASCII JSON: {error}") from error
    if canonical_json(state).encode("ascii") != raw:
        raise ValueError("M102 state bytes are not canonical JSON")
    state = _closed(
        state,
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
    payload = {key: value for key, value in state.items() if key != "state_digest"}
    if state["schema"] != STATE_SCHEMA:
        raise ValueError("M102 state schema mismatch")
    if state["state_digest"] != digest(payload):
        raise ValueError("M102 state digest mismatch")
    if not isinstance(state["m101_ascii"], str) or not isinstance(state["m101_sha256"], str):
        raise ValueError("M102 predecessor binding is invalid")
    predecessor_raw = state["m101_ascii"].encode("ascii")
    measured_m101 = hashlib.sha256(predecessor_raw).hexdigest()
    if measured_m101 != state["m101_sha256"]:
        raise ValueError("M101 predecessor bytes changed")
    if expected_m101_sha256 is not None and measured_m101 != expected_m101_sha256:
        raise ValueError("M101 predecessor differs from the independently expected digest")
    predecessor_report = m101_checker.validate(
        predecessor_raw, expected_m100_sha256=expected_m100_sha256
    )
    if predecessor_report["definition_count"] != 2:
        raise ValueError("M102 predecessor is not exact M101 T2 shape")
    a_id = predecessor_report["definitions"][0]["definition_id"]
    b_id = predecessor_report["definitions"][1]["definition_id"]

    policy, policy_report = _validate_policy(state["policy"])
    if not isinstance(state["journal"], list):
        raise ValueError("M102 journal is invalid")
    journal = [_validate_event(item) for item in state["journal"]]
    event_ids = [item["event_id"] for item in journal]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("M102 journal contains duplicate events")
    registry, rows = _rebuild_registry(policy, journal)

    c_report: dict[str, Any] | None = None
    if state["c_definition"] is not None:
        _c, c_report = _validate_c(
            state["c_definition"],
            a_id=str(a_id),
            b_id=str(b_id),
            policy_id=str(policy["policy_id"]),
        )

    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "scientific_verdict": False,
        "confirmed": True,
        "state_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "state_digest": state["state_digest"],
        "m101_sha256": measured_m101,
        "m100_sha256": predecessor_report["m100_sha256"],
        "m101_definition_ids": [a_id, b_id],
        "predecessor_report_digest": predecessor_report["report_digest"],
        "policy": policy_report,
        "journal_event_count": len(journal),
        "journal_event_ids": event_ids,
        "registry_entry_count": len(registry),
        "registry_rows": rows,
        "registry_digest": digest(registry),
        "c_definition": c_report,
        "independent_of_m102_runtime_and_search": True,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--expected-m101-sha256")
    parser.add_argument("--expected-m100-sha256")
    arguments = parser.parse_args()
    try:
        report = validate(
            Path(arguments.state).read_bytes(),
            expected_m101_sha256=arguments.expected_m101_sha256,
            expected_m100_sha256=arguments.expected_m100_sha256,
        )
    except Exception as error:
        report = {
            "schema": REPORT_SCHEMA,
            "scientific_verdict": False,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
            "independent_of_m102_runtime_and_search": True,
        }
        report["report_digest"] = digest(report)
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
