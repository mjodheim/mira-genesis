"""Minimal isolated entry point for M103 state transitions and consumers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import m103_runtime as runtime


PROCESS_SCHEMA = "m103-isolated-process-v1"


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


def _facts(raw: bytes, state: dict[str, Any]) -> dict[str, Any]:
    summary = runtime.state_summary(state)
    return {
        "input_state_digest": state["state_digest"],
        "input_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "input_m102_sha256": state["m102_sha256"],
        "input_constructor_id": state["constructor"]["constructor_id"],
        "input_definition_ids": summary["definition_ids"],
    }


def _write_acquisition(
    arguments: argparse.Namespace, acquisition: dict[str, Any]
) -> tuple[str | None, str | None]:
    next_state = acquisition.get("next_state")
    if arguments.register and acquisition.get("confirmed") is True:
        if not isinstance(next_state, dict):
            raise ValueError("registered acquisition produced no next state")
        raw = runtime.encode_state(next_state)
        return next_state["state_digest"], _write(arguments.out, raw)
    if arguments.out is not None:
        raise ValueError("an output path is allowed only for successful registration")
    return None, None


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    action = str(arguments.action)
    if action == "create-state":
        if arguments.m102 is None:
            raise ValueError("M102 U2 bytes are required")
        predecessor = Path(arguments.m102).read_bytes()
        state = runtime.create_state(predecessor)
        raw = runtime.encode_state(state)
        return _envelope(
            action,
            {
                "confirmed": True,
                "m102_sha256": hashlib.sha256(predecessor).hexdigest(),
                "output_state_digest": state["state_digest"],
                "output_raw_sha256": _write(arguments.out, raw),
                "summary": runtime.state_summary(state),
            },
        )

    state_raw, state = _state(arguments.state)
    facts = _facts(state_raw, state)
    if action == "acquire-constructor":
        demand = runtime.decode_demand(_canonical_value(arguments.demand, "M103 demand"))
        acquisition = runtime.acquire_constructor(
            state, demand, register_result=bool(arguments.register)
        )
        output_digest, output_sha256 = _write_acquisition(arguments, acquisition)
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
    if action == "acquire-consumer":
        demand = runtime.decode_demand(_canonical_value(arguments.demand, "M103 demand"))
        acquisition = runtime.acquire_consumer(
            state, demand, register_result=bool(arguments.register)
        )
        output_digest, output_sha256 = _write_acquisition(arguments, acquisition)
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
    if action == "execute-world":
        world = _canonical_value(arguments.world, "M103 execution world")
        execution = runtime.execute_world(state, world)
        return _envelope(
            action,
            {**facts, "confirmed": execution["confirmed"], "execution": execution},
        )
    if action == "conservation":
        report = runtime.predecessor_conservation(state)
        confirmed = all(
            bool(report[key])
            for key in (
                "m100_live",
                "m101_a_live",
                "m101_b_live",
                "m102_k_live",
                "m102_c_live",
                "record_registry_live",
            )
        )
        return _envelope(action, {**facts, "confirmed": confirmed, "conservation": report})
    if action == "state-control":
        control = str(arguments.control)
        if control == "constructor-ablate":
            output = runtime.encode_state(runtime.ablate_constructor(state))
        elif control == "constructor-mutate":
            output = runtime.encode_state(runtime.mutate_constructor_without_partition(state))
        elif control == "configuration-ablate":
            output = runtime.encode_state(runtime.ablate_family(state, "configuration"))
        elif control == "filesystem-ablate":
            output = runtime.encode_state(runtime.ablate_family(state, "filesystem"))
        elif control == "corrupt":
            output = runtime.corrupt_state_digest(state)
        else:
            raise ValueError("unknown M103 state control")
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
            raise ValueError("rollback input does not differ from accepted state")
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
    raise ValueError("unknown M103 action")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "create-state",
            "acquire-constructor",
            "acquire-consumer",
            "execute-world",
            "conservation",
            "state-control",
            "rollback",
        ),
    )
    parser.add_argument("--m102")
    parser.add_argument("--state")
    parser.add_argument("--demand")
    parser.add_argument("--world")
    parser.add_argument("--out")
    parser.add_argument("--restore")
    parser.add_argument("--register", action="store_true")
    parser.add_argument(
        "--control",
        choices=(
            "constructor-ablate",
            "constructor-mutate",
            "configuration-ablate",
            "filesystem-ablate",
            "corrupt",
        ),
    )
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
