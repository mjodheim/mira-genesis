"""Reproduce M065 independently and compare exact bytes to the first result."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform

from run_m065_canonical import canonical_bytes, canonical_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marker-parent-sha", required=True)
    parser.add_argument("--canonical-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    first = args.canonical_result.read_bytes()
    reproduced = canonical_bytes(canonical_result(args.marker_parent_sha))
    report = {
        "schema": "m065-independent-reproduction-v1",
        "marker_parent_sha": args.marker_parent_sha,
        "python_runtime": platform.python_version(),
        "first_result_sha256": hashlib.sha256(first).hexdigest(),
        "reproduced_result_sha256": hashlib.sha256(reproduced).hexdigest(),
        "exact_bytes_reproduced": reproduced == first,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["exact_bytes_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
