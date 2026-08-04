from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.m041_engine import run_m041_development


def _json_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = run_m041_development()
    payload = _json_value(result.mapping())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "gates_one_to_nine_supported": result.gates_one_to_nine_supported,
        "eligible_for_freeze": result.eligible_for_freeze,
        "result_digest": result.digest(),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
