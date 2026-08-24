"""Minimal isolated entry point for M105 state transitions and consumers."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

if (Path(__file__).resolve().parent / "m105_runtime.py").exists():
    runtime = importlib.import_module("m105_runtime")
else:  # pragma: no cover - normal repository import
    from metamorphosis import m105_runtime as runtime


PROCESS_SCHEMA = "m105-isolated-process-v1"


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
        "input_m104_sha256": state["m104_sha256"],
        "input_feature_ids": summary["feature_ids"],
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
        if arguments.m104 is None:
            raise ValueError("exact M104 V3 bytes are required")
        predecessor = Path(arguments.m104).read_bytes()
        state = runtime.create_state(predecessor)
        raw = runtime.encode_state(state)
        return _envelope(
            action,
            {
                "confirmed": True,
                "m104_sha256": hashlib.sha256(predecessor).hexdigest(),
                "output_state_digest": state["state_digest"],
                "output_raw_sha256": _write(arguments.out, raw),
                "summary": runtime.state_summary(state),
            },
        )

    state_raw, state = _state(arguments.state)
    facts = _facts(state_raw, state)
    if action == "acquire-feature":
        demand = runtime.decode_feature_demand(
            _canonical_value(arguments.demand, "M105 feature demand")
        )
        acquisition = runtime.acquire_feature(
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
        demand = runtime.decode_consumer_demand(
            _canonical_value(arguments.demand, "M105 consumer demand")
        )
        repetitions = int(arguments.repetitions)
        if not 1 <= repetitions <= 100:
            raise ValueError("M105 acquisition repetitions are out of bounds")
        if arguments.register and repetitions != 1:
            raise ValueError("registered acquisition cannot be repeated")
        attempts = [
            runtime.acquire_consumer(
                state, demand, register_result=bool(arguments.register)
            )
            for _index in range(repetitions)
        ]
        acquisition = attempts[-1]
        stable_attempts = [
            {key: value for key, value in attempt.items() if key != "next_state"}
            for attempt in attempts
        ]
        output_digest, output_sha256 = _write_acquisition(arguments, acquisition)
        return _envelope(
            action,
            {
                **facts,
                "confirmed": acquisition["confirmed"],
                "acquisition": acquisition,
                "repetitions": repetitions,
                "repeated_image_identical": all(
                    attempt == stable_attempts[0] for attempt in stable_attempts
                ),
                "output_state_digest": output_digest,
                "output_raw_sha256": output_sha256,
            },
        )
    if action == "execute-definition":
        execution = _canonical_value(arguments.execution, "M105 execution request")
        execution = runtime._closed(  # noqa: SLF001 - closed capsule boundary
            execution,
            {"definition_id", "context", "initial"},
            "M105 execution request",
        )
        output = runtime.execute_definition(
            state,
            execution["definition_id"],
            execution["context"],
            execution["initial"],
        )
        return _envelope(
            action,
            {**facts, "confirmed": True, "execution_output": output},
        )
    if action == "conservation":
        report = runtime.predecessor_conservation(state)
        return _envelope(
            action,
            {**facts, "confirmed": report["all_conserved"], "conservation": report},
        )
    if action == "semantic-census":
        report = runtime.semantic_census()
        return _envelope(
            action,
            {
                **facts,
                "confirmed": report["complete_two_input_boolean_image"],
                "semantic_census": report,
            },
        )
    if action == "state-control":
        control = str(arguments.control)
        if control == "feature-mutate-rebind":
            output = runtime.encode_state(runtime.mutate_feature_and_rebind(state))
        elif control == "feature-remove":
            output = runtime.canonical_json(
                runtime.remove_feature_without_rebinding(state)
            ).encode("ascii")
        elif control == "corrupt":
            output = runtime.canonical_json(runtime.corrupt_state_digest(state)).encode(
                "ascii"
            )
        else:
            raise ValueError("unknown M105 state control")
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
    raise ValueError("unknown M105 action")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "create-state",
            "acquire-feature",
            "acquire-consumer",
            "execute-definition",
            "conservation",
            "semantic-census",
            "state-control",
            "rollback",
        ),
    )
    parser.add_argument("--m104")
    parser.add_argument("--state")
    parser.add_argument("--demand")
    parser.add_argument("--execution")
    parser.add_argument("--out")
    parser.add_argument("--restore")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument(
        "--control",
        choices=("feature-mutate-rebind", "feature-remove", "corrupt"),
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
