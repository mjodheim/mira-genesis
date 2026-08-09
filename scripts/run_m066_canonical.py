"""Run and serialise the unique marker-selected M066 canonical result."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from metamorphosis.m066_canonical_governance import run_m066_canonical


def canonical_result(marker_parent_sha: str) -> dict[str, object]:
    manifest = run_m066_canonical(marker_parent_sha)
    return {
        "schema": "m066-canonical-result-v1",
        "marker_parent_sha": marker_parent_sha,
        "manifest_digest": manifest.digest(),
        "manifest": manifest.to_dict(),
    }


def canonical_bytes(result: dict[str, object]) -> bytes:
    return (json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marker-parent-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = canonical_result(args.marker_parent_sha)
    payload = canonical_bytes(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(
        json.dumps(
            {
                "output_sha256": hashlib.sha256(payload).hexdigest(),
                "manifest_digest": result["manifest_digest"],
                "selected_bank_index": result["manifest"]["selected_bank_index"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
