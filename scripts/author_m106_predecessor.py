"""Extract the exact positive M104 V3 predecessor for M106 authoring."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_RESULT_DIGEST = "f2be4d8516207187f0892eb6c8cecd0f648563456f33aa07fe13787b0e867de3"
EXPECTED_RAW_SHA256 = "98d61df076e6b764f6b00f27793b82ef27e20cd35049780499029dc3ed7edf77"
EXPECTED_STATE_DIGEST = "a34b3b9dab99ee848a9c209a95ec9201fd7056eb99393d45d4041c885f19417a"
EXPECTED_LENGTH = 8011


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def extract(result_path: Path) -> bytes:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("result_digest") != EXPECTED_RESULT_DIGEST:
        raise ValueError("M104 result digest mismatch")
    state = result["scientific_evidence"]["states"]["V3"]["state"]
    raw = canonical_json(state).encode("ascii")
    if len(raw) != EXPECTED_LENGTH:
        raise ValueError("M104 V3 length mismatch")
    if hashlib.sha256(raw).hexdigest() != EXPECTED_RAW_SHA256:
        raise ValueError("M104 V3 raw digest mismatch")
    if state.get("state_digest") != EXPECTED_STATE_DIGEST:
        raise ValueError("M104 V3 state digest mismatch")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", default="experiments/M104/RESULT.json")
    parser.add_argument("--out", default="experiments/M106/M104_V3.json")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raw = extract(Path(arguments.result))
    target = Path(arguments.out)
    if arguments.check:
        if not target.exists() or target.read_bytes() != raw:
            raise SystemExit("M106 predecessor fixture differs from exact M104 V3")
        return 0
    if target.exists():
        raise SystemExit("M106 predecessor fixture already exists")
    target.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
