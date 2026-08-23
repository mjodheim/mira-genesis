"""Minimal isolated entry point for M101 state transitions and baseline controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import m101_runtime as runtime


def _demand(path: str | None) -> dict[str, object]:
    if path is None:
        raise ValueError("a public-demand path is required")
    raw = Path(path).read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"public demand is not canonical ASCII JSON: {error}") from error
    if runtime.canonical_json(value).encode("ascii") != raw:
        raise ValueError("public demand bytes are not canonical JSON")
    return runtime.decode_public_demand(value)


def _state(path: str | None) -> tuple[bytes, dict[str, object]]:
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


def _envelope(action: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "m101-acquisition-process-v1",
        "action": action,
        "pid": os.getpid(),
        "isolated_mode": sys.flags.isolated == 1,
        "imported_project_modules": sorted(
            name
            for name in sys.modules
            if name.startswith(("metamorphosis", "scripts", "mira_core"))
        ),
        "search_path": [str(item) for item in sys.path],
        **payload,
    }


def run(arguments: argparse.Namespace) -> dict[str, object]:
    action = str(arguments.action)
    if action == "create-state":
        if arguments.m100 is None:
            raise ValueError("M100 predecessor bytes are required")
        m100_bytes = Path(arguments.m100).read_bytes()
        state = runtime.create_state(m100_bytes)
        raw = runtime.encode_state(state)
        output_sha256 = _write(arguments.out, raw)
        return _envelope(
            action,
            {
                "confirmed": True,
                "m100_sha256": hashlib.sha256(m100_bytes).hexdigest(),
                "output_state_digest": state["state_digest"],
                "output_raw_sha256": output_sha256,
                "definition_count": 0,
            },
        )

    state_raw, state = _state(arguments.state)
    state_facts = {
        "input_state_digest": state["state_digest"],
        "input_raw_sha256": hashlib.sha256(state_raw).hexdigest(),
        "m100_sha256": state["m100_sha256"],
        "input_definition_count": len(state["definitions"]),
    }
    if action == "baseline":
        if state["definitions"]:
            raise ValueError("fresh baseline requires T0 without registered M101 definitions")
        result = runtime.baseline(_demand(arguments.demand))
        return _envelope(
            action,
            {**state_facts, "confirmed": result["reachable"] is False, "baseline": result},
        )

    if action in {"acquire-a", "acquire-b"}:
        demand = _demand(arguments.demand)
        register_result = bool(arguments.register)
        if action == "acquire-a":
            acquisition = runtime.acquire_a(state, demand, register_result=register_result)
        else:
            acquisition = runtime.acquire_b(state, demand, register_result=register_result)
        next_state = acquisition.get("next_state")
        output_digest = None
        output_sha256 = None
        if register_result and acquisition.get("confirmed") is True:
            if not isinstance(next_state, dict):
                raise ValueError("registered acquisition produced no state")
            output_raw = runtime.encode_state(next_state)
            output_sha256 = _write(arguments.out, output_raw)
            output_digest = next_state["state_digest"]
        elif arguments.out is not None:
            raise ValueError("an output path is allowed only for a successful registration")
        return _envelope(
            action,
            {
                **state_facts,
                "confirmed": acquisition["confirmed"],
                "acquisition": acquisition,
                "output_state_digest": output_digest,
                "output_raw_sha256": output_sha256,
            },
        )

    if action == "state-control":
        kind = str(arguments.control)
        if kind == "rewrite-a":
            output_raw = runtime.encode_state(runtime.rewrite_a_order_for_fault(state))
        elif kind == "ablate-a":
            output_raw = runtime.ablate_a_raw(state)
        elif kind == "ablate-b":
            output_raw = runtime.encode_state(runtime.ablate_b(state))
        elif kind == "corrupt":
            output_raw = runtime.corrupt_state_digest(state)
        else:
            raise ValueError("unknown M101 state control")
        output_sha256 = _write(arguments.out, output_raw)
        return _envelope(
            action,
            {
                **state_facts,
                "confirmed": True,
                "control": kind,
                "output_raw_sha256": output_sha256,
                "output_differs": output_raw != state_raw,
            },
        )
    if action == "rollback":
        if arguments.restore is None:
            raise ValueError("exact rollback bytes are required")
        restore_raw = Path(arguments.restore).read_bytes()
        restored = runtime.decode_state(restore_raw)
        if restore_raw == state_raw:
            raise ValueError("rollback input does not differ from the accepted state")
        output_sha256 = _write(arguments.out, restore_raw)
        return _envelope(
            action,
            {
                **state_facts,
                "confirmed": True,
                "restored_state_digest": restored["state_digest"],
                "restored_raw_sha256": output_sha256,
                "restoration_is_byte_exact": True,
            },
        )
    raise ValueError("unknown M101 acquisition action")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "create-state", "baseline", "acquire-a", "acquire-b", "state-control", "rollback"
        ),
    )
    parser.add_argument("--m100")
    parser.add_argument("--state")
    parser.add_argument("--demand")
    parser.add_argument("--out")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--control", choices=("rewrite-a", "ablate-a", "ablate-b", "corrupt"))
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
