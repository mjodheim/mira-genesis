"""Independently close the inherited M103 S0 constructive image for one demand."""

from __future__ import annotations

import argparse
import configparser
import copy
import hashlib
import itertools
import json
from io import StringIO
from pathlib import Path
from typing import Any


STATE_SCHEMA = "m103-lineage-state-v1"
CONSTRUCTOR_SCHEMA = "m103-hypothesis-constructor-v1"
ACTION_SCHEMA = "m103-action-v1"
DEMAND_SCHEMA = "m103-acquisition-demand-v1"
S0_ORIGIN = "m103-inherited-s0"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _read_canonical(path: Path, label: str) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not canonical ASCII JSON: {error}") from error
    if canonical_json(value).encode("ascii") != raw or not isinstance(value, dict):
        raise ValueError(f"{label} bytes are not a canonical object")
    return value


def _validate_s0(state: dict[str, Any]) -> dict[str, Any]:
    state = _closed(
        state,
        {
            "schema",
            "m102_sha256",
            "m102_ascii",
            "constructor",
            "definitions",
            "state_digest",
        },
        "M103 state",
    )
    payload = {key: value for key, value in state.items() if key != "state_digest"}
    if state["schema"] != STATE_SCHEMA or state["state_digest"] != digest(payload):
        raise ValueError("M103 state schema/digest mismatch")
    constructor = _closed(
        copy.deepcopy(state["constructor"]),
        {"schema", "constructor_id", "origin", "features"},
        "M103 constructor",
    )
    if (
        constructor["schema"] != CONSTRUCTOR_SCHEMA
        or constructor["origin"] != S0_ORIGIN
        or constructor["features"] != []
    ):
        raise ValueError("M103 closure requires exact inherited S0")
    address = {
        "schema": CONSTRUCTOR_SCHEMA,
        "origin": S0_ORIGIN,
        "features": [],
    }
    if constructor["constructor_id"] != f"constructor-s0-{digest(address)[:16]}":
        raise ValueError("M103 S0 content address mismatch")
    return state


def _validate_demand(demand: dict[str, Any]) -> dict[str, Any]:
    demand = _closed(
        demand,
        {
            "schema",
            "demand_id",
            "family",
            "actions",
            "public_cases",
            "diagnostic_probes",
            "max_trace",
        },
        "M103 demand",
    )
    if demand["schema"] != DEMAND_SCHEMA or demand["family"] not in {
        "development_record",
        "configuration",
        "filesystem",
    }:
        raise ValueError("M103 demand schema/family mismatch")
    if not isinstance(demand["max_trace"], int) or not 1 <= demand["max_trace"] <= 3:
        raise ValueError("M103 demand bound is invalid")
    if not isinstance(demand["actions"], list) or not demand["actions"]:
        raise ValueError("M103 demand actions are missing")
    actions: list[dict[str, Any]] = []
    for raw in demand["actions"]:
        action = _closed(
            copy.deepcopy(raw), {"schema", "action_id", "descriptor"}, "M103 action"
        )
        payload = {"schema": ACTION_SCHEMA, "descriptor": action["descriptor"]}
        if action["schema"] != ACTION_SCHEMA or action["action_id"] != f"action-{digest(payload)[:16]}":
            raise ValueError("M103 action content address mismatch")
        actions.append(action)
    demand["actions"] = actions
    if not isinstance(demand["public_cases"], list) or not demand["public_cases"]:
        raise ValueError("M103 public cases are missing")
    for case in demand["public_cases"]:
        _closed(case, {"case_id", "context", "initial", "expected"}, "M103 public case")
        if not isinstance(case["context"], list) or not case["context"]:
            raise ValueError("M103 public context is invalid")
    return demand


def _record(descriptor: dict[str, Any], value: Any) -> Any:
    if not isinstance(value, dict):
        raise ValueError("record input is invalid")
    out = copy.deepcopy(value)
    kind = descriptor.get("kind")
    if kind == "set_value" and isinstance(descriptor.get("key"), str):
        out[descriptor["key"]] = copy.deepcopy(descriptor.get("value"))
    elif kind == "drop_value" and isinstance(descriptor.get("key"), str):
        out.pop(descriptor["key"], None)
    elif kind == "rename_value" and isinstance(descriptor.get("old"), str) and isinstance(
        descriptor.get("new"), str
    ):
        if descriptor["old"] in out:
            out[descriptor["new"]] = out.pop(descriptor["old"])
    else:
        raise ValueError("unknown record descriptor")
    return out


def _config(descriptors: list[dict[str, Any]], initial: Any) -> dict[str, dict[str, str]]:
    if not isinstance(initial, str):
        raise ValueError("configuration input is invalid")
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_file(StringIO(initial))
    for descriptor in descriptors:
        section = descriptor.get("section")
        if not isinstance(section, str):
            raise ValueError("configuration section is invalid")
        if not parser.has_section(section):
            parser.add_section(section)
        kind = descriptor.get("kind")
        if kind == "set_option" and isinstance(descriptor.get("option"), str) and isinstance(
            descriptor.get("value"), str
        ):
            parser.set(section, descriptor["option"], descriptor["value"])
        elif kind == "remove_option" and isinstance(descriptor.get("option"), str):
            parser.remove_option(section, descriptor["option"])
        elif kind == "rename_option" and isinstance(descriptor.get("old"), str) and isinstance(
            descriptor.get("new"), str
        ):
            if parser.has_option(section, descriptor["old"]):
                value = parser.get(section, descriptor["old"])
                parser.remove_option(section, descriptor["old"])
                parser.set(section, descriptor["new"], value)
        else:
            raise ValueError("unknown configuration descriptor")
    return {
        section: {key: parser.get(section, key) for key in sorted(parser[section])}
        for section in sorted(parser.sections())
    }


def _filesystem(descriptors: list[dict[str, Any]], initial: Any) -> dict[str, str]:
    if not isinstance(initial, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in initial.items()
    ):
        raise ValueError("filesystem input is invalid")
    out = copy.deepcopy(initial)
    for descriptor in descriptors:
        kind = descriptor.get("kind")
        if kind == "write_text" and isinstance(descriptor.get("path"), str) and isinstance(
            descriptor.get("content"), str
        ):
            out[descriptor["path"]] = descriptor["content"]
        elif kind == "append_text" and isinstance(descriptor.get("path"), str) and isinstance(
            descriptor.get("content"), str
        ):
            out[descriptor["path"]] = out.get(descriptor["path"], "") + descriptor["content"]
        elif kind == "delete_path" and isinstance(descriptor.get("path"), str):
            out.pop(descriptor["path"], None)
        elif kind == "rename_path" and isinstance(descriptor.get("old"), str) and isinstance(
            descriptor.get("new"), str
        ):
            if descriptor["old"] in out:
                out[descriptor["new"]] = out.pop(descriptor["old"])
        else:
            raise ValueError("unknown filesystem descriptor")
    return dict(sorted(out.items()))


def _execute(demand: dict[str, Any], body: tuple[str, ...], initial: Any) -> Any:
    catalogue = {action["action_id"]: action["descriptor"] for action in demand["actions"]}
    descriptors = [catalogue[action_id] for action_id in body]
    if demand["family"] == "development_record":
        value = copy.deepcopy(initial)
        for descriptor in descriptors:
            value = _record(descriptor, value)
        return value
    if demand["family"] == "configuration":
        return _config(descriptors, initial)
    return _filesystem(descriptors, initial)


def close(state: dict[str, Any], demand: dict[str, Any]) -> dict[str, Any]:
    _validate_s0(state)
    demand = _validate_demand(demand)
    action_ids = [action["action_id"] for action in demand["actions"]]
    traces = [
        body
        for length in range(1, demand["max_trace"] + 1)
        for body in itertools.product(action_ids, repeat=length)
    ]
    accepted: list[list[str]] = []
    for body in traces:
        try:
            if all(
                _execute(demand, body, case["initial"]) == case["expected"]
                for case in demand["public_cases"]
            ):
                accepted.append(list(body))
        except Exception:
            continue
    witnesses: list[dict[str, Any]] = []
    for index, left in enumerate(demand["public_cases"]):
        for right in demand["public_cases"][index + 1 :]:
            if (
                left["initial"] == right["initial"]
                and left["context"] != right["context"]
                and left["expected"] != right["expected"]
            ):
                witnesses.append(
                    {
                        "left_case_id": left["case_id"],
                        "right_case_id": right["case_id"],
                        "same_initial_digest": digest(left["initial"]),
                        "contexts_distinct": True,
                        "expected_outputs_distinct": True,
                    }
                )
    report: dict[str, Any] = {
        "schema": "m103-independent-s0-closure-v1",
        "scientific_verdict": False,
        "confirmed": bool(witnesses) and not accepted,
        "demand_id": demand["demand_id"],
        "family": demand["family"],
        "finite_image_size": len(traces),
        "enumerated": len(traces),
        "accepted": len(accepted),
        "accepted_bodies": accepted,
        "same_input_distinct_context_output_witnesses": witnesses,
        "actions_receive_context": False,
        "s0_reads_context": False,
        "budget_independent_invariant": "equal deterministic input plus one global trace implies equal output",
        "independent_of_m103_runtime_and_search": True,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--demand", required=True)
    arguments = parser.parse_args()
    try:
        report = close(
            _read_canonical(Path(arguments.state), "M103 state"),
            _read_canonical(Path(arguments.demand), "M103 demand"),
        )
    except Exception as error:
        report = {
            "schema": "m103-independent-s0-closure-v1",
            "scientific_verdict": False,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
            "independent_of_m103_runtime_and_search": True,
        }
        report["report_digest"] = digest(report)
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
