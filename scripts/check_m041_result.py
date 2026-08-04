from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from metamorphosis.m041_result_verify import verify_m041_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()

    raw = args.artifact.read_bytes()
    envelope = json.loads(raw)
    result = envelope.get("result", envelope)
    verify_m041_result(
        result,
        raw_bytes=raw if args.expected_sha256 is not None else None,
        expected_sha256=args.expected_sha256,
    )
    print(json.dumps({
        "verified": True,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "all_ten_gates_supported": bool(result["all_ten_gates_supported"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
