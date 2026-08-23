"""Minimal isolated entry point for M102 state transitions and causal controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import m102_runtime as runtime


PROCESS_SCHEMA = "m102-acquisition-process-v1"


def _canonical_value(path: str | None, label: str) -> Any:
    if path is None:
        raise ValueError(f"a {label} path is required")
    raw = Path(path).read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not canonical ASCII JSON: {error}") from error
    if runtime.canonical_json(value).encode("ascii") != raw:
        raise ValueError(f"{label} bytes are not canonical JSON")
    return value


def _state(path: str | None) -> tuple[bytes, dict[str, Any]]:
    if path is None:
        raise ValueError("a lineage-state path is required")
    raw = Path(path).read_bytes()
    return raw, runtime.decode_state(raw)


def _events(path: str | None) -> list[dict[str, Any]]:
    value = _canonical_value(path, "event journal fragment")
    if not isinstance(value, list):
        raise ValueError("event journal fragment is not a list")
    return [runtime.decode_event(item) for item in value]


def _write(path: str | None, raw: bytes) -> str:
    if path is None:
        raise ValueError("an output-state path is required")
    target = Path(path)
    if target.exists():
        raise ValueError("output state already exists")
    target.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _envelope(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": PROCESS_SCHEMA,
        "action": action,
        "pid": os.getpid(),
        "isolated_mode": sys.flags.isolated == 1,
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
        "runtime_identity": runtime.runtime_identity(),
        "imported_project_modules": sorted(
            name
            for name in sys.modules
            if name.startswith(("metamorphosis", "scripts", "mira_core"))
        ),
        "search_path": [str(item) for item in sys.path],
        **payload,
    }


def _state_facts(raw: bytes, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "input_state_digest": state["state_digest"],
        "input_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "m101_sha256": state["m101_sha256"],
        "input_policy_id": state["policy"]["policy_id"],
        "input_event_count": len(state["journal"]),
        "input_c_definition_id": (
            state["c_definition"]["definition_id"]
            if state["c_definition"] is not None
            else None
        ),
    }


def _write_registered(
    arguments: argparse.Namespace,
    acquisition: dict[str, Any],
) -> tuple[str | None, str | None]:
    next_state = acquisition.get("next_state")
    if bool(arguments.register) and acquisition.get("confirmed") is True:
        if not isinstance(next_state, dict):
            raise ValueError("registered acquisition produced no state")
        output = runtime.encode_state(next_state)
        return str(next_state["state_digest"]), _write(arguments.out, output)
    if arguments.out is not None:
        raise ValueError("an output path is allowed only for successful registration")
    return None, None


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    action = str(arguments.action)
    if action == "create-state":
        if arguments.m101 is None:
            raise ValueError("M101 predecessor bytes are required")
        predecessor = Path(arguments.m101).read_bytes()
        state = runtime.create_state(predecessor, _events(arguments.events))
        output = runtime.encode_state(state)
        output_sha256 = _write(arguments.out, output)
        return _envelope(
            action,
            {
                "confirmed": True,
                "m101_sha256": hashlib.sha256(predecessor).hexdigest(),
                "output_state_digest": state["state_digest"],
                "output_raw_sha256": output_sha256,
                "output_policy_id": state["policy"]["policy_id"],
                "output_event_count": len(state["journal"]),
            },
        )

    state_raw, state = _state(arguments.state)
    facts = _state_facts(state_raw, state)
    if action == "acquire-policy":
        demand = runtime.decode_policy_demand(_canonical_value(arguments.demand, "policy demand"))
        acquisition = runtime.acquire_policy(
            state, demand, register_result=bool(arguments.register)
        )
        output_digest, output_sha256 = _write_registered(arguments, acquisition)
        return _envelope(
            action,
            {
                **facts,
                "confirmed": acquisition["confirmed"],
                "acquisition": acquisition,
                "output_state_digest": output_digest,
                "output_raw_sha256": output_sha256,
            },
        )
    if action == "register-events":
        next_state = runtime.register_events(state, _events(arguments.events))
        output = runtime.encode_state(next_state)
        return _envelope(
            action,
            {
                **facts,
                "confirmed": True,
                "output_state_digest": next_state["state_digest"],
                "output_raw_sha256": _write(arguments.out, output),
                "output_event_count": len(next_state["journal"]),
            },
        )
    if action == "force-last-write":
        next_state = runtime.force_last_write_events(state, _events(arguments.events))
        output = runtime.encode_state(next_state)
        return _envelope(
            action,
            {
                **facts,
                "confirmed": True,
                "control": "destructive-no-upgrade-last-write",
                "output_state_digest": next_state["state_digest"],
                "output_raw_sha256": _write(arguments.out, output),
                "output_event_count": len(next_state["journal"]),
            },
        )
    if action == "acquire-c":
        demand = runtime.decode_c_demand(_canonical_value(arguments.demand, "C demand"))
        acquisition = runtime.acquire_c(
            state, demand, register_result=bool(arguments.register)
        )
        output_digest, output_sha256 = _write_registered(arguments, acquisition)
        return _envelope(
            action,
            {
                **facts,
                "confirmed": acquisition["confirmed"],
                "acquisition": acquisition,
                "output_state_digest": output_digest,
                "output_raw_sha256": output_sha256,
            },
        )
    if action == "state-control":
        control = str(arguments.control)
        if control == "flat-policy":
            output = runtime.encode_state(runtime.mutate_policy_to_flat(state))
        elif control == "c-duplicate":
            output = runtime.encode_state(runtime.mutate_c_duplicate_effect(state))
        elif control == "c-ablate":
            output = runtime.encode_state(runtime.ablate_c(state))
        elif control == "b-order":
            output = runtime.encode_state(runtime.mutate_m101_b_order(state))
        elif control == "b-ablate":
            output = runtime.ablate_m101_b_raw(state)
        elif control == "corrupt":
            output = runtime.corrupt_state_digest(state)
        else:
            raise ValueError("unknown M102 state control")
        return _envelope(
            action,
            {
                **facts,
                "confirmed": True,
                "control": control,
                "output_raw_sha256": _write(arguments.out, output),
                "output_differs": output != state_raw,
            },
        )
    if action == "rollback":
        if arguments.restore is None:
            raise ValueError("exact rollback bytes are required")
        restore_raw = Path(arguments.restore).read_bytes()
        restored = runtime.decode_state(restore_raw)
        if restore_raw == state_raw:
            raise ValueError("rollback input does not differ from the accepted state")
        return _envelope(
            action,
            {
                **facts,
                "confirmed": True,
                "restored_state_digest": restored["state_digest"],
                "restored_raw_sha256": _write(arguments.out, restore_raw),
                "restoration_is_byte_exact": True,
            },
        )
    raise ValueError("unknown M102 acquisition action")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "create-state",
            "acquire-policy",
            "register-events",
            "force-last-write",
            "acquire-c",
            "state-control",
            "rollback",
        ),
    )
    parser.add_argument("--m101")
    parser.add_argument("--state")
    parser.add_argument("--events")
    parser.add_argument("--demand")
    parser.add_argument("--out")
    parser.add_argument("--register", action="store_true")
    parser.add_argument(
        "--control",
        choices=("flat-policy", "c-duplicate", "c-ablate", "b-order", "b-ablate", "corrupt"),
    )
    parser.add_argument("--restore")
    arguments = parser.parse_args()
    try:
        result = run(arguments)
    except Exception as error:
        result = _envelope(
            str(arguments.action),
            {
                "confirmed": False,
                "failed_closed": True,
                "error": f"{type(error).__name__}: {error}",
            },
        )
        print(json.dumps(result, sort_keys=True))
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0 if result["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
