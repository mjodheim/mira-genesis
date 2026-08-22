"""Persist M097's accepted registry in a process that then exits completely."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m097-result", required=True)
    parser.add_argument("--state-out", required=True)
    parser.add_argument("--manifest-out", required=True)
    args = parser.parse_args()
    result = json.loads(Path(args.m097_result).read_text(encoding="utf-8"))
    serialized = result["scientific_evidence"]["serialized_state"]
    parsed = json.loads(serialized)
    if canonical_json(parsed) != serialized:
        raise ValueError("M097 serialized state is not canonical")
    state_path = Path(args.state_out)
    state_path.write_bytes(serialized.encode("ascii"))
    manifest = {
        "schema": "m098-persist-manifest-v1",
        "producer_pid": os.getpid(),
        "m097_result_digest": result["result_digest"],
        "state_digest": parsed["state_digest"],
        "state_raw_sha256": hashlib.sha256(serialized.encode("ascii")).hexdigest(),
        "bytes_written": len(serialized.encode("ascii")),
    }
    Path(args.manifest_out).write_text(
        canonical_json(manifest) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
